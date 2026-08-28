package dev.guides.distributed.boundary;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class ServiceBoundary {
    // [Implementation 1] 변경되지 않는 검토 입력
    // DataSet, Service, Architecture가 Set과 List를 복사해 검토 도중 입력이 바뀌지 않게 합니다.
    public record DataSet(String name, String owner, Set<String> writers) {
        public DataSet {
            writers = Set.copyOf(writers);
        }
    }

    public record Service(String name, Set<String> synchronousDependencies) {
        public Service {
            synchronousDependencies = Set.copyOf(synchronousDependencies);
        }
    }

    public record Architecture(List<Service> services, List<DataSet> dataSets) {
        public Architecture {
            services = List.copyOf(services);
            dataSets = List.copyOf(dataSets);
        }
    }

    // [Implementation 2] 서비스·소유자·writer·의존 대상 검증
    // review는 등록되지 않은 이름과 소유자가 아닌 writer를 한 번의 순회에서 모두 수집합니다.
    public static List<String> review(Architecture architecture) {
        Set<String> serviceNames = new LinkedHashSet<>();
        List<String> issues = new ArrayList<>();
        for (Service service : architecture.services()) {
            if (!serviceNames.add(service.name())) {
                issues.add("duplicate service: " + service.name());
            }
        }

        for (DataSet dataSet : architecture.dataSets()) {
            if (!serviceNames.contains(dataSet.owner())) {
                issues.add(
                    "unknown owner for " + dataSet.name() + ": " + dataSet.owner()
                );
            }
            if (!dataSet.writers().contains(dataSet.owner())) {
                issues.add("owner is not a writer for " + dataSet.name());
            }
            for (String writer : dataSet.writers()) {
                if (!serviceNames.contains(writer)) {
                    issues.add(
                        "unknown writer for " + dataSet.name() + ": " + writer
                    );
                } else if (!writer.equals(dataSet.owner())) {
                    issues.add(
                        "non-owner writer for " + dataSet.name() + ": " + writer
                    );
                }
            }
        }

        Map<String, Set<String>> dependencies = new HashMap<>();
        for (Service service : architecture.services()) {
            dependencies.put(service.name(), service.synchronousDependencies());
            for (String dependency : service.synchronousDependencies()) {
                if (!serviceNames.contains(dependency)) {
                    issues.add(
                        "unknown dependency from " + service.name() + ": " + dependency
                    );
                }
            }
        }

        return List.copyOf(issues);
    }
}
