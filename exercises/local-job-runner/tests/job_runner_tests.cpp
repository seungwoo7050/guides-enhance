#include "job_runner.hpp"

#include <cassert>
#include <chrono>
#include <condition_variable>
#include <filesystem>
#include <fstream>
#include <future>
#include <iterator>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <type_traits>

using namespace std::chrono_literals;
using jobs::JobId;
using jobs::JobRunner;
using jobs::JobStatus;
using jobs::SubmitError;

static_assert(!std::is_convertible_v<std::uint64_t, JobId>);
static_assert(!std::is_copy_constructible_v<JobRunner>);
static_assert(!std::is_move_constructible_v<JobRunner>);

namespace {
std::string read_text(const std::filesystem::path& path) {
    std::ifstream input{path};
    return {std::istreambuf_iterator<char>{input}, std::istreambuf_iterator<char>{}};
}
} // namespace

int main() {
    const auto root = std::filesystem::temp_directory_path() /
                      ("job-runner-test-" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    std::filesystem::create_directories(root);

    bool zero_rejected = false;
    try {
        JobRunner invalid{root / "zero.tsv", 0};
    }
    catch (const std::invalid_argument&) {
        zero_rejected = true;
    }
    assert(zero_rejected);

    JobRunner runner{root / "jobs.tsv", 1};
    assert(runner.journal_healthy());
    assert(!runner.snapshot(JobId{999}));
    assert(!runner.wait_for_terminal(JobId{999}, 500ms));

    const auto empty_name = runner.submit("", [](std::stop_token) { return std::string{}; });
    assert(!empty_name && empty_name.error() == SubmitError::empty_name);
    const auto empty_work = runner.submit("empty", jobs::Work{});
    assert(!empty_work && empty_work.error() == SubmitError::empty_work);

    const auto success = runner.submit("success", [](std::stop_token) { return std::string{"done"}; });
    assert(success);
    assert(runner.wait_for_terminal(success.value(), 2s));
    const auto success_state = runner.snapshot(success.value());
    assert(success_state && success_state->status == JobStatus::succeeded);
    assert(success_state->output == "done");

    const auto failure = runner.submit("failure", [](std::stop_token) -> std::string {
        throw std::runtime_error("boom");
    });
    assert(failure && runner.wait_for_terminal(failure.value(), 2s));
    const auto failure_state = runner.snapshot(failure.value());
    assert(failure_state && failure_state->status == JobStatus::failed);
    assert(failure_state->error == "boom");

    std::promise<void> started;
    std::promise<void> release;
    const auto gate = release.get_future().share();
    const auto blocking = runner.submit("blocking", [&started, gate](std::stop_token) {
        started.set_value();
        gate.wait();
        return std::string{"released"};
    });
    assert(blocking);
    assert(started.get_future().wait_for(2s) == std::future_status::ready);

    const auto queued = runner.submit("queued", [](std::stop_token) { return std::string{"queued"}; });
    assert(queued);
    // 첫 작업의 시작을 확인한 뒤 queue를 채워 scheduling과 무관하게 queue_full을 만듭니다.
    const auto overflow = runner.submit("overflow", [](std::stop_token) { return std::string{}; });
    assert(!overflow && overflow.error() == SubmitError::queue_full);
    assert(runner.cancel(queued.value()));
    assert(runner.wait_for_terminal(queued.value(), 2s));
    assert(runner.snapshot(queued.value())->status == JobStatus::cancelled);
    release.set_value();
    assert(runner.wait_for_terminal(blocking.value(), 2s));

    std::promise<void> cancel_started;
    // callback이 stop_token을 확인해야 running 작업이 cancelled로 끝나는지 검증합니다.
    const auto cancellable = runner.submit("cancellable", [&cancel_started](std::stop_token token) {
        cancel_started.set_value();
        std::mutex mutex;
        std::condition_variable_any changed;
        std::unique_lock lock{mutex};
        changed.wait(lock, token, [] { return false; });
        return std::string{"stop observed"};
    });
    assert(cancellable);
    assert(cancel_started.get_future().wait_for(2s) == std::future_status::ready);
    assert(runner.cancel(cancellable.value()));
    assert(runner.wait_for_terminal(cancellable.value(), 2s));
    assert(runner.snapshot(cancellable.value())->status == JobStatus::cancelled);

    // 반복 호출이 중복 join이나 deadlock을 만들지 않아야 합니다.
    runner.stop();
    runner.stop();
    const auto late = runner.submit("late", [](std::stop_token) { return std::string{}; });
    assert(!late && late.error() == SubmitError::stopped);

    // 작업 결과와 journal 행이 같은 최종 상태를 가리키는지 확인합니다.
    const std::string journal = read_text(root / "jobs.tsv");
    assert(journal.find("\tsucceeded\tsuccess\tdone") != std::string::npos);
    assert(journal.find("\tfailed\tfailure\tboom") != std::string::npos);
    assert(journal.find("\tcancelled\tcancellable\t") != std::string::npos);

    std::filesystem::remove_all(root);
}
