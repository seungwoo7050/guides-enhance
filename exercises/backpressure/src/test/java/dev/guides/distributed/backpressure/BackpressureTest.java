package dev.guides.distributed.backpressure;

import dev.guides.distributed.testing.Checks;

public final class BackpressureTest {
    public static void main(String[] args) {
        queueIsBoundedAndShedsExcessLoad();
        lanesDoNotShareFailureCapacity();
        completionPromotesExactlyOneQueuedRequest();
        expiredQueuedWorkIsNeverPromoted();
        System.out.println("backpressure tests passed");
    }

    private static void queueIsBoundedAndShedsExcessLoad() {
        Backpressure.AdmissionSystem system = new Backpressure.AdmissionSystem();
        system.register("inventory", 1, 1);

        Checks.equals(
            Backpressure.Admission.STARTED,
            system.submit("inventory", "i-1"),
            "The first request must start"
        );
        Checks.equals(
            Backpressure.Admission.QUEUED,
            system.submit("inventory", "i-2"),
            "The second request must enter the bounded queue"
        );
        Checks.equals(
            Backpressure.Admission.REJECTED,
            system.submit("inventory", "i-3"),
            "Excess load must be rejected"
        );
        Checks.equals(1, system.inFlight("inventory"), "In-flight work must remain bounded");
        Checks.equals(1, system.queued("inventory"), "Queued work must remain bounded");
        Checks.equals(1, system.rejected("inventory"), "Rejection evidence must be observable");
    }

    private static void lanesDoNotShareFailureCapacity() {
        Backpressure.AdmissionSystem system = new Backpressure.AdmissionSystem();
        system.register("email", 1, 0);
        system.register("inventory", 1, 0);

        Checks.equals(
            Backpressure.Admission.STARTED,
            system.submit("email", "e-1"),
            "The first email request must start"
        );
        Checks.equals(
            Backpressure.Admission.REJECTED,
            system.submit("email", "e-2"),
            "A saturated lane must reject excess work"
        );
        Checks.equals(
            Backpressure.Admission.STARTED,
            system.submit("inventory", "i-1"),
            "Saturation in one lane must not consume another lane"
        );
    }

    private static void completionPromotesExactlyOneQueuedRequest() {
        Backpressure.AdmissionSystem system = new Backpressure.AdmissionSystem();
        system.register("inventory", 1, 2);
        system.submit("inventory", "i-1");
        system.submit("inventory", "i-2");
        system.submit("inventory", "i-3");

        String promoted = system.completeOne("inventory");

        Checks.equals("i-2", promoted, "FIFO promotion must choose the oldest request");
        Checks.isTrue(system.completed("inventory", "i-1"), "Completed work must be recorded");
        Checks.equals(1, system.inFlight("inventory"), "Only one request may run");
        Checks.equals(1, system.queued("inventory"), "One request must remain queued");
        Checks.isFalse(system.completed("inventory", "i-3"), "Queued work must not look complete");
    }

    private static void expiredQueuedWorkIsNeverPromoted() {
        Backpressure.AdmissionSystem system = new Backpressure.AdmissionSystem();
        system.register("payments", 1, 2, 20);
        system.submit("payments", "p-1", 0, 100);
        system.submit("payments", "p-2", 5, 100);
        system.submit("payments", "p-3", 15, 100);

        Checks.equals(13L, system.oldestQueueAge("payments", 18), "Oldest wait must be observable");
        Checks.equals(1, system.expire("payments", 26), "Only the expired head must be removed");
        Checks.equals(1, system.queued("payments"), "A valid later request must remain queued");
        Checks.equals("p-3", system.completeOne("payments", 26), "Only valid work may be promoted");
        Checks.equals(1, system.expired("payments"), "Expiry evidence must be accumulated");

        Checks.equals(
            Backpressure.Admission.REJECTED,
            system.submit("payments", "p-late", 30, 30),
            "An already expired request must be rejected immediately"
        );
        Checks.equals(2, system.expired("payments"), "Deadline expiry must be recorded");
    }
}
