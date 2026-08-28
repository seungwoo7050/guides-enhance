package dev.guides.distributed.observability;

import dev.guides.distributed.testing.Checks;
import java.util.List;
import java.util.Set;

public final class ObservabilityCorrelationTest {
    public static void main(String[] args) {
        identifiersRemainConnectedAcrossHops();
        duplicateDeliveryIsVisibleWithoutDuplicateEffect();
        conflictingIdentifiersAreRejectedBeforeEvidence();
        metricsUseBoundedTagKeys();
        traceAndMetricContractsAreExplicit();
        explicitIngressIdentifiersRemainConnected();
        System.out.println("observability-correlation tests passed");
    }

    private static void identifiersRemainConnectedAcrossHops() {
        ObservabilityCorrelation.Flow flow = new ObservabilityCorrelation.Flow();
        ObservabilityCorrelation.Command command =
            flow.receive("req-17", "op-42", "reservation-9");
        ObservabilityCorrelation.Event event = flow.publish(command);
        flow.consume(event);

        List<ObservabilityCorrelation.Observation> observations = flow.observations();
        Checks.equals(3, observations.size(), "Three processing boundaries must be observed");
        for (ObservabilityCorrelation.Observation observation : observations) {
            Checks.equals(
                "req-17",
                observation.correlationId(),
                "Every hop must preserve correlation identity"
            );
            Checks.equals(
                "trace-req-17",
                observation.traceId(),
                "Every hop must preserve trace identity"
            );
            Checks.equals(
                "op-42",
                observation.operationId(),
                "Every hop must preserve operation identity"
            );
        }
        Checks.equals("op-42", event.causationId(), "The event must identify its command cause");
        Checks.equals("reservation-9", event.aggregateId(), "The business aggregate must be preserved");
    }

    private static void duplicateDeliveryIsVisibleWithoutDuplicateEffect() {
        ObservabilityCorrelation.Flow flow = new ObservabilityCorrelation.Flow();
        ObservabilityCorrelation.Command command =
            flow.receive("req-18", "op-43", "reservation-10");
        ObservabilityCorrelation.Event event = flow.publish(command);

        flow.consume(event);
        flow.consume(event);

        Checks.equals(1, flow.effects(), "Duplicate delivery must preserve one business effect");
        Checks.equals(
            1,
            flow.metricCount("inventory", "duplicate"),
            "Duplicate attempts must remain observable"
        );
    }

    private static void conflictingIdentifiersAreRejectedBeforeEvidence() {
        ObservabilityCorrelation.Flow flow = new ObservabilityCorrelation.Flow();
        ObservabilityCorrelation.Event original = new ObservabilityCorrelation.Event(
            "evt-shared", "op-50", "trace-a", "req-a", "op-50", "reservation-20"
        );
        ObservabilityCorrelation.Event conflict = new ObservabilityCorrelation.Event(
            "evt-shared", "op-51", "trace-b", "req-b", "op-51", "reservation-21"
        );
        flow.consume(original);
        int observationsBefore = flow.observations().size();

        Checks.throwsType(
            IllegalArgumentException.class,
            () -> flow.consume(conflict),
            "Conflicting identity linkage must fail before evidence is recorded"
        );
        Checks.equals(1, flow.effects(), "A conflict must not add a business effect");
        Checks.equals(
            observationsBefore,
            flow.observations().size(),
            "A conflict must not add misleading observations"
        );
    }

    private static void metricsUseBoundedTagKeys() {
        ObservabilityCorrelation.Flow flow = new ObservabilityCorrelation.Flow();
        Checks.equals(
            Set.of("component", "outcome"),
            flow.metricTagKeys(),
            "Metrics must expose only bounded tag keys"
        );
    }

    private static void traceAndMetricContractsAreExplicit() {
        ObservabilityCorrelation.Flow flow = new ObservabilityCorrelation.Flow();
        ObservabilityCorrelation.Command command =
            flow.receive("req-19", "op-44", "reservation-11");
        Checks.isFalse(
            command.traceId().equals(command.operationId()),
            "Trace and operation identity have different lifecycles"
        );
        flow.validateMetricTagKeys(Set.of("component", "outcome"));
        Checks.throwsType(
            IllegalArgumentException.class,
            () -> flow.validateMetricTagKeys(Set.of("component", "operationId")),
            "High-cardinality identity must not become a metric tag"
        );
    }

    private static void explicitIngressIdentifiersRemainConnected() {
        ObservabilityCorrelation.Flow flow = new ObservabilityCorrelation.Flow();
        ObservabilityCorrelation.Command command = flow.receive(
            "req-upstream",
            "op-upstream",
            "trace-upstream",
            "corr-business-flow",
            "reservation-upstream"
        );
        ObservabilityCorrelation.Event event = flow.publish(command);
        flow.consume(event);

        Checks.equals("trace-upstream", command.traceId(), "Upstream trace identity must be preserved");
        Checks.equals(
            "corr-business-flow",
            command.correlationId(),
            "Upstream correlation identity must not be replaced by request identity"
        );
        for (ObservabilityCorrelation.Observation observation : flow.observations()) {
            Checks.equals("trace-upstream", observation.traceId(), "Trace continuity must hold");
            Checks.equals(
                "corr-business-flow",
                observation.correlationId(),
                "Correlation continuity must hold"
            );
        }
    }
}
