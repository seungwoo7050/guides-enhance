#ifndef LOCAL_JOB_RUNNER_JOB_RUNNER_HPP
#define LOCAL_JOB_RUNNER_JOB_RUNNER_HPP

#include "result.hpp"

#include <chrono>
#include <compare>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <filesystem>
#include <functional>
#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <stop_token>
#include <string>
#include <string_view>
#include <thread>

namespace jobs {
// [Implementation 2] Job identifiers, states, snapshots, and work callbacks

class JobId {
public:
    explicit constexpr JobId(std::uint64_t value) noexcept : value_(value) {}
    [[nodiscard]] constexpr std::uint64_t value() const noexcept { return value_; }
    auto operator<=>(const JobId&) const = default;

private:
    std::uint64_t value_;
};

enum class JobStatus {
    queued,
    running,
    succeeded,
    failed,
    cancelled
};

enum class SubmitError {
    stopped,
    queue_full,
    empty_name,
    empty_work
};

struct JobSnapshot {
    JobId id;
    std::string name;
    JobStatus status;
    std::string output;
    std::string error;
};

using Work = std::function<std::string(std::stop_token)>;
using SubmitResult = Result<JobId, SubmitError>;

[[nodiscard]] std::string_view to_string(JobStatus status) noexcept;

// [Implementation 3] Own queued work, records, cancellation sources, and worker state
// JobRunner가 queue, Record, stop_source와 worker의 join 상태를 모두 소유합니다.
class JobRunner {
public:
    JobRunner(std::filesystem::path journal_path, std::size_t queue_capacity);
    ~JobRunner();

    JobRunner(const JobRunner&) = delete;
    JobRunner& operator=(const JobRunner&) = delete;
    JobRunner(JobRunner&&) = delete;
    JobRunner& operator=(JobRunner&&) = delete;

    [[nodiscard]] SubmitResult submit(std::string name, Work work);
    [[nodiscard]] bool cancel(JobId id);
    [[nodiscard]] std::optional<JobSnapshot> snapshot(JobId id) const;
    [[nodiscard]] bool wait_for_terminal(JobId id, std::chrono::milliseconds timeout);
    [[nodiscard]] bool journal_healthy() const;

    void stop();

private:
    struct Record {
        JobSnapshot snapshot;
        Work work;
        std::stop_source cancellation;
    };

    static bool is_terminal(JobStatus status) noexcept;
    void run(std::stop_token stop_token);
    void append_transition_locked(const JobSnapshot& snapshot) noexcept;
    void join_worker();

    std::filesystem::path journal_path_;
    std::size_t queue_capacity_;
    mutable std::mutex mutex_;
    std::condition_variable_any work_available_;
    std::condition_variable terminal_changed_;
    std::deque<JobId> queue_;
    std::map<JobId, std::unique_ptr<Record>> records_;
    std::uint64_t next_id_{1};
    bool accepting_{true};
    bool journal_healthy_{true};

    std::mutex join_mutex_;
    std::condition_variable join_changed_;
    bool join_started_{false};
    bool joined_{false};
    std::stop_source worker_stop_source_;
    std::thread::id worker_id_;
    std::jthread worker_;
};
} // namespace jobs

#endif
