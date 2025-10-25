package controllers

import (
	"encoding/json"
	"net/http"
	"time"
)

// ErrorResponse represents an API error response
type ErrorResponse struct {
	Error     string    `json:"error"`
	Code      int       `json:"code"`
	Message   string    `json:"message"`
	Timestamp time.Time `json:"timestamp"`
}

// SuccessResponse represents a generic success response
type SuccessResponse struct {
	Success   bool        `json:"success"`
	Data      interface{} `json:"data,omitempty"`
	Message   string      `json:"message,omitempty"`
	Timestamp time.Time   `json:"timestamp"`
}

// sendError sends a JSON error response
func sendError(w http.ResponseWriter, message string, statusCode int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)

	errorResponse := ErrorResponse{
		Error:     http.StatusText(statusCode),
		Code:      statusCode,
		Message:   message,
		Timestamp: time.Now(),
	}

	json.NewEncoder(w).Encode(errorResponse)
}

// sendSuccess sends a JSON success response
func sendSuccess(w http.ResponseWriter, data interface{}, message string, statusCode int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)

	successResponse := SuccessResponse{
		Success:   true,
		Data:      data,
		Message:   message,
		Timestamp: time.Now(),
	}

	json.NewEncoder(w).Encode(successResponse)
}

// sendData sends a JSON response with just the data
func sendData(w http.ResponseWriter, data interface{}, statusCode int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(data)
}
