package dev.guides.distributed.observability;
import dev.guides.distributed.testing.Checks;
public final class ObservabilityCorrelationTest {
public static void main(String[] args) {
var flow = new ObservabilityCorrelation.Flow();
var command = flow.receive("request", "operation", "upstream-trace", "correlation", "aggregate");
var event = flow.publish(command);
Checks.equals("upstream-trace", event.traceId(), "Trace preserved");
Checks.equals("correlation", event.correlationId(), "Correlation preserved");
Checks.equals("operation", event.causationId(), "Causation preserved");
Checks.equals(2, flow.observations().size(), "Ingress and publication evidence");
System.out.println("stage tests passed");
}

}
