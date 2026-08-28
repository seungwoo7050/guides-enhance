#include "job_runner.hpp"

#include <array>
#include <chrono>
#include <exception>
#include <filesystem>
#include <iostream>
#include <stop_token>
#include <string>
#include <utility>
#include <vector>

using namespace std::chrono_literals;

// [Implementation 10] Run sample jobs and map failures to exit status
// 제출·대기·상태 조회 실패를 표준 오류와 종료 상태로 바꿉니다.
int main(int argc, char* argv[]) {
    if (argc != 2) {
        std::cerr << "usage: local_job_runner_app <journal-path>\n";
        return 2;
    }

    try {
        jobs::JobRunner runner{std::filesystem::path{argv[1]}, 4};
        const std::array tasks{
            std::pair{std::string{"compile"}, std::string{"compile-ready"}},
            std::pair{std::string{"test"}, std::string{"tests-passed"}},
            std::pair{std::string{"package"}, std::string{"package-ready"}},
        };

        std::vector<jobs::JobId> ids;
        for (const auto& [name, output] : tasks) {
            auto submitted = runner.submit(name, [output](std::stop_token) { return output; });
            if (!submitted) {
                std::cerr << "submission rejected\n";
                return 1;
            }
            ids.push_back(submitted.value());
        }

        for (const jobs::JobId id : ids) {
            if (!runner.wait_for_terminal(id, 2s))
                return 1;
            const auto state = runner.snapshot(id);
            if (!state)
                return 1;
            std::cout << id.value() << ' ' << jobs::to_string(state->status);
            if (!state->output.empty())
                std::cout << ' ' << state->output;
            std::cout << '\n';
            if (state->status != jobs::JobStatus::succeeded)
                return 1;
        }
        runner.stop();
    }
    catch (const std::exception& exception) {
        std::cerr << "local job runner failed: " << exception.what() << '\n';
        return 1;
    }
}
