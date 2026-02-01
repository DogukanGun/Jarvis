package main

import (
	"encoding/base64"
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
	"time"
)

// PubSubMessage is the payload Google Pub/Sub sends to the push endpoint.
type PubSubMessage struct {
	Message struct {
		Data string `json:"data"`
	} `json:"message"`
}

// WebhookEvent is the decoded event pushed to the channel for the agent.
type WebhookEvent struct {
	EmailAddress string    `json:"emailAddress"`
	HistoryID    int64     `json:"historyId"`
	ReceivedAt   time.Time `json:"receivedAt"`
}

func decodePubSubData(data string) (WebhookEvent, error) {
	base64Std := strings.ReplaceAll(strings.ReplaceAll(data, "-", "+"), "_", "/")
	raw, err := base64.StdEncoding.DecodeString(base64Std)
	if err != nil {
		return WebhookEvent{}, err
	}

	var decoded struct {
		EmailAddress string      `json:"emailAddress"`
		HistoryID    interface{} `json:"historyId"`
	}
	if err := json.Unmarshal(raw, &decoded); err != nil {
		return WebhookEvent{}, err
	}

	var historyID int64
	switch v := decoded.HistoryID.(type) {
	case string:
		historyID, _ = strconv.ParseInt(v, 10, 64)
	case float64:
		historyID = int64(v)
	case int:
		historyID = int64(v)
	case int64:
		historyID = v
	}

	return WebhookEvent{
		EmailAddress: decoded.EmailAddress,
		HistoryID:    historyID,
		ReceivedAt:   time.Now().UTC(),
	}, nil
}

func handleWebhook(verificationToken string, events chan<- WebhookEvent) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}

		token := r.URL.Query().Get("token")
		if verificationToken == "" {
			http.Error(w, `{"message":"Webhook not configured"}`, http.StatusInternalServerError)
			w.Header().Set("Content-Type", "application/json")
			return
		}
		if token != verificationToken {
			w.Header().Set("Content-Type", "application/json")
			http.Error(w, `{"message":"Invalid verification token"}`, http.StatusForbidden)
			return
		}

		var body PubSubMessage
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			w.Header().Set("Content-Type", "application/json")
			http.Error(w, `{"message":"Invalid body"}`, http.StatusBadRequest)
			return
		}

		if body.Message.Data == "" {
			w.Header().Set("Content-Type", "application/json")
			http.Error(w, `{"message":"No data found"}`, http.StatusBadRequest)
			return
		}

		event, err := decodePubSubData(body.Message.Data)
		if err != nil {
			w.Header().Set("Content-Type", "application/json")
			http.Error(w, `{"message":"Failed to decode data"}`, http.StatusBadRequest)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"ok":true}`))

		if events != nil {
			select {
			case events <- event:
			default:
			}
		}
	}
}
