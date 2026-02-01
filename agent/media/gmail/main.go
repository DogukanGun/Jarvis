package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"sync"
)

func main() {
	verificationToken := os.Getenv("GOOGLE_PUBSUB_VERIFICATION_TOKEN")
	addr := os.Getenv("PORT")
	if addr == "" {
		addr = "8080"
	}
	webhookPath := os.Getenv("WEBHOOK_PATH")
	if webhookPath == "" {
		webhookPath = "/webhook"
	}

	eventBufferSize := 100
	events := make(chan WebhookEvent, eventBufferSize)

	http.HandleFunc(webhookPath, handleWebhook(verificationToken, events))
	http.HandleFunc("/events", streamEvents())

	log.Printf("Listening on %s, webhook at %s, SSE at /events", addr, webhookPath)

	go broadcastEvents(events)

	if err := http.ListenAndServe(":"+addr, nil); err != nil {
		log.Fatal(err)
	}
}

var (
	subMu    sync.Mutex
	subscribers []chan<- WebhookEvent
)

// broadcastEvents reads from the channel, logs, and fans out to SSE subscribers.
// Your agent can also read from the same channel by starting before ListenAndServe
// and sharing the events channel (e.g. when embedding this as a library).
func broadcastEvents(events <-chan WebhookEvent) {
	for event := range events {
		log.Printf("event: email=%s historyId=%d", event.EmailAddress, event.HistoryID)
		subMu.Lock()
		for _, ch := range subscribers {
			select {
			case ch <- event:
			default:
			}
		}
		subMu.Unlock()
	}
}

// streamEvents serves Server-Sent Events so an external agent can subscribe.
func streamEvents() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}

		w.Header().Set("Content-Type", "text/event-stream")
		w.Header().Set("Cache-Control", "no-cache")
		w.Header().Set("Connection", "keep-alive")
		w.Header().Set("X-Accel-Buffering", "no")
		flusher, ok := w.(http.Flusher)
		if !ok {
			http.Error(w, "streaming unsupported", http.StatusInternalServerError)
			return
		}

		ch := make(chan WebhookEvent, 8)
		subMu.Lock()
		subscribers = append(subscribers, ch)
		subMu.Unlock()
		defer func() {
			subMu.Lock()
			for i, c := range subscribers {
				if c == ch {
					subscribers = append(subscribers[:i], subscribers[i+1:]...)
					break
				}
			}
			subMu.Unlock()
			close(ch)
		}()

		for event := range ch {
			b, _ := json.Marshal(event)
			_, _ = w.Write([]byte("event: email\ndata: " + string(b) + "\n\n"))
			flusher.Flush()
		}
	}
}
