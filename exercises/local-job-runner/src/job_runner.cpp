#include "job_runner.hpp"

#include <algorithm>
#include <fstream>
#include <ranges>
#include <stdexcept>
#include <utility>

namespace jobs {
namespace {
void write_journal_field(std::ostream& output, std::string_view text) {
    for (const char character : text) {
        if (character == '\t' || character == '\n' || character == '\r')
            output.put(' ');
        else
            output.put(character);
    }
}
} // namespace

std::string_view to_string(JobStatus status) noexcept {
    switch (status) {
    case JobStatus::queued:
        return "queued";
    case JobStatus::running:
        return "running";
    case JobStatus::succeeded:
        return "succeeded";
    case JobStatus::failed:
        return "failed";
    case JobStatus::cancelled:
        return "cancelled";
    }
    return "unknown";
}

// [Implementation 4] Validate capacity and journal before starting the worker
// capacity와 journal을 먼저 확인해 생성 실패 뒤 worker가 남지 않게 합니다.
JobRunner::JobRunner(std::filesystem::path journal_path, std::size_t queue_capacity)
    : journal_path_(std::move(journal_path)), queue_capacity_(queue_capacity) {
    if (queue_capacity_ == 0)
        throw std::invalid_argument("queue capacity must be greater than zero");

    if (journal_path_.has_parent_path())
        std::filesystem::create_directories(journal_path_.parent_path());
    std::ofstream probe{journal_path_, std::ios::app};
    if (!probe)
        throw std::runtime_error("cannot open job journal");

    worker_ = std::jthread([this](std::stop_token token) { run(token); });
    worker_stop_source_ = worker_.get_stop_source();
    worker_id_ = worker_.get_id();
}

JobRunner::~JobRunner() {
    stop();
}

// [Implementation 5] Insert the record and queue entry as one operation
// 입력 거부는 값으로 반환하고, Record와 queue 삽입은 함께 성공하거나 함께 취소합니다.
SubmitResult JobRunner::submit(std::string name, Work work) {
    if (name.empty())
        return SubmitResult::failure(SubmitError::empty_name);
    if (!work)
        return SubmitResult::failure(SubmitError::empty_work);

    JobId id{0};
    {
        std::lock_guard lock{mutex_};
        if (!accepting_)
            return SubmitResult::failure(SubmitError::stopped);
        if (queue_.size() >= queue_capacity_)
            return SubmitResult::failure(SubmitError::queue_full);

        id = JobId{next_id_++};
        auto record = std::make_unique<Record>(Record{
            JobSnapshot{id, std::move(name), JobStatus::queued, {}, {}},
            std::move(work),
            {},
        });
        const auto [position, inserted] = records_.emplace(id, std::move(record));
        if (!inserted)
            throw std::overflow_error("job id space exhausted");
        try {
            queue_.push_back(id);
        }
        catch (...) {
            records_.erase(position);
            throw;
        }
        append_transition_locked(position->second->snapshot);
    }
    work_available_.notify_one();
    return SubmitResult::success(id);
}

// [Implementation 6] Cancel queued work or request cooperative stop
// 대기 작업은 즉시 취소하고, 실행 작업에는 stop 요청만 전달합니다.
bool JobRunner::cancel(JobId id) {
    bool cancellation_changed = false;
    bool terminal_changed = false;
    {
        std::lock_guard lock{mutex_};
        const auto found = records_.find(id);
        if (found == records_.end() || is_terminal(found->second->snapshot.status))
            return false;

        Record& record = *found->second;
        if (record.snapshot.status == JobStatus::queued) {
            const auto queued = std::ranges::find(queue_, id);
            if (queued != queue_.end())
                queue_.erase(queued);
            record.snapshot.status = JobStatus::cancelled;
            append_transition_locked(record.snapshot);
            cancellation_changed = true;
            terminal_changed = true;
        }
        else {
            cancellation_changed = record.cancellation.request_stop();
        }
    }

    if (terminal_changed)
        terminal_changed_.notify_all();
    return cancellation_changed;
}

std::optional<JobSnapshot> JobRunner::snapshot(JobId id) const {
    std::lock_guard lock{mutex_};
    const auto found = records_.find(id);
    if (found == records_.end())
        return std::nullopt;
    return found->second->snapshot;
}

bool JobRunner::wait_for_terminal(JobId id, std::chrono::milliseconds timeout) {
    std::unique_lock lock{mutex_};
    if (!records_.contains(id))
        return false;

    return terminal_changed_.wait_for(lock, timeout, [this, id] {
        return is_terminal(records_.at(id)->snapshot.status);
    });
}

bool JobRunner::journal_healthy() const {
    std::lock_guard lock{mutex_};
    return journal_healthy_;
}

bool JobRunner::is_terminal(JobStatus status) noexcept {
    return status == JobStatus::succeeded || status == JobStatus::failed ||
           status == JobStatus::cancelled;
}

// [Implementation 7] Move jobs from queued to a terminal state in the worker
// running 이후 상태는 worker만 바꾸며 callback 예외는 failed 상태에 저장합니다.
void JobRunner::run(std::stop_token stop_token) {
    while (true) {
        Record* record = nullptr;
        {
            std::unique_lock lock{mutex_};
            work_available_.wait(lock, stop_token, [this] {
                return !queue_.empty() || !accepting_;
            });

            if (queue_.empty())
                return;

            const JobId id = queue_.front();
            queue_.pop_front();
            record = records_.at(id).get();
            if (record->snapshot.status == JobStatus::cancelled)
                continue;
            record->snapshot.status = JobStatus::running;
            append_transition_locked(record->snapshot);
        }

        std::string output;
        std::string error;
        JobStatus final_status = JobStatus::succeeded;
        try {
            output = record->work(record->cancellation.get_token());
        }
        catch (const std::exception& exception) {
            final_status = JobStatus::failed;
            error = exception.what();
        }
        catch (...) {
            final_status = JobStatus::failed;
            error = "unknown exception";
        }

        {
            std::lock_guard lock{mutex_};
            if (final_status == JobStatus::succeeded &&
                record->cancellation.stop_requested()) {
                final_status = JobStatus::cancelled;
            }
            record->snapshot.status = final_status;
            record->snapshot.output = std::move(output);
            record->snapshot.error = std::move(error);
            append_transition_locked(record->snapshot);
        }
        terminal_changed_.notify_all();
    }
}

// [Implementation 8] Keep journal failure separate from job completion
// journal 기록 실패는 계속 남기되 작업 결과를 덮어쓰지 않습니다.
void JobRunner::append_transition_locked(const JobSnapshot& snapshot) noexcept {
    try {
        std::ofstream journal{journal_path_, std::ios::app};
        if (!journal) {
            journal_healthy_ = false;
            return;
        }

        const std::string_view message =
            snapshot.error.empty() ? std::string_view{snapshot.output}
                                   : std::string_view{snapshot.error};
        journal << snapshot.id.value() << '\t' << to_string(snapshot.status) << '\t';
        write_journal_field(journal, snapshot.name);
        journal.put('\t');
        write_journal_field(journal, message);
        journal.put('\n');
        journal.flush();
        if (!journal)
            journal_healthy_ = false;
    }
    catch (...) {
        journal_healthy_ = false;
    }
}

// [Implementation 9] Stop submissions, request cancellation, and join safely
// 새 제출을 막고 취소를 전달한 뒤, worker 자신이 아닌 호출자만 join합니다.
void JobRunner::stop() {
    {
        std::lock_guard lock{mutex_};
        if (accepting_) {
            accepting_ = false;

            for (const JobId id : queue_) {
                Record& record = *records_.at(id);
                record.snapshot.status = JobStatus::cancelled;
                record.cancellation.request_stop();
                append_transition_locked(record.snapshot);
            }
            queue_.clear();

            for (auto& [id, record] : records_) {
                static_cast<void>(id);
                if (record->snapshot.status == JobStatus::running)
                    record->cancellation.request_stop();
            }
        }
    }

    worker_stop_source_.request_stop();
    work_available_.notify_all();
    terminal_changed_.notify_all();
    join_worker();
}

void JobRunner::join_worker() {
    if (std::this_thread::get_id() == worker_id_)
        return;

    std::unique_lock join_lock{join_mutex_};
    while (!joined_ && join_started_)
        join_changed_.wait(join_lock, [this] { return joined_ || !join_started_; });
    if (joined_)
        return;

    join_started_ = true;
    join_lock.unlock();

    try {
        if (worker_.joinable())
            worker_.join();
    }
    catch (...) {
        join_lock.lock();
        join_started_ = false;
        join_lock.unlock();
        join_changed_.notify_all();
        throw;
    }

    join_lock.lock();
    joined_ = true;
    join_lock.unlock();
    join_changed_.notify_all();
}
} // namespace jobs
