package main

import (
    "context"
    "fmt"
    "log"
    "time"

    "sensorfuzz/scheduler/pkg/scheduler"
)

func main() {
    ctx := context.Background()
    queue := scheduler.NewRedisQueue("redis://localhost:6379/0", "sensor-fuzz-tasks")
    worker := scheduler.NewWorker(queue, func(t scheduler.Task) scheduler.Result {
        // Placeholder handler: simulate processing time
        time.Sleep(10 * time.Millisecond)
        return scheduler.Result{TaskID: t.ID, Status: "done", Details: "ok"}
    })
    worker.Start(ctx)

    // Enqueue demo tasks
    for i := 0; i < 3; i++ {
        err := queue.Enqueue(ctx, scheduler.Task{ID: fmt.Sprintf("task-%d", i), Protocol: "mqtt", Payload: map[string]string{"topic": "demo"}, Priority: 1})
        if err != nil {
            log.Printf("enqueue error: %v", err)
        }
    }

    time.Sleep(1 * time.Second)
    worker.Stop()
}
