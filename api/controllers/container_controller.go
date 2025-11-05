package controllers

import (
	"encoding/json"
	"jarvis/api/data"
	"jarvis/api/services"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"
)

type ContainerController struct {
	containerManager *services.ContainerManager
	invoiceManager   *services.InvoiceManager
	userManager      *services.UserManager
}

func NewContainerController(containerManager *services.ContainerManager, userManager *services.UserManager, invoiceManager *services.InvoiceManager) *ContainerController {
	return &ContainerController{
		containerManager: containerManager,
		userManager:      userManager,
		invoiceManager:   invoiceManager,
	}
}

// MessageRequest represents a message request to a container
type MessageRequest struct {
	Message string `json:"message" validate:"required"`
}

// MessageResponse represents a message response from a container
type MessageResponse struct {
	Response    string    `json:"response"`
	ProcessedAt time.Time `json:"processed_at"`
	UserID      string    `json:"user_id"`
	ContainerID string    `json:"container_id"`
}

// ContainerStatusResponse represents container status information
type ContainerStatusResponse struct {
	ContainerID string    `json:"container_id"`
	UserID      string    `json:"user_id"`
	Status      string    `json:"status"`
	Port        int       `json:"port"`
	Created     time.Time `json:"created"`
	LastUsed    time.Time `json:"last_used"`
	IsRunning   bool      `json:"is_running"`
}

// SendMessage sends a message to the authenticated user's container
// @Summary Send message to user's agent
// @Description Sends a message to the user's Jarvis agent running in their dedicated container
// @Tags Agent Communication
// @Accept json
// @Produce json
// @Param request body MessageRequest true "Message data"
// @Param Authorization header string true "Bearer token"
// @Success 200 {object} MessageResponse "Message processed successfully"
// @Failure 400 {object} ErrorResponse "Invalid request body"
// @Failure 401 {object} ErrorResponse "Unauthorized"
// @Failure 404 {object} ErrorResponse "Container not found"
// @Failure 500 {object} ErrorResponse "Internal server error"
// @Router /api/v1/containers/message [post]
func (cc *ContainerController) SendMessage(w http.ResponseWriter, r *http.Request) {
	authUser := GetAuthenticatedUser(r)
	if authUser == nil {
		sendError(w, "Authentication required", http.StatusUnauthorized)
		return
	}

	var req MessageRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		sendError(w, "Invalid JSON payload", http.StatusBadRequest)
		return
	}

	if req.Message == "" {
		sendError(w, "Message is required", http.StatusBadRequest)
		return
	}

	// Get user's container ID
	user, err := cc.userManager.GetUser(authUser.UserID)
	if err != nil {
		sendError(w, "User not found", http.StatusNotFound)
		return
	}

	if user.ContainerID == "" {
		sendError(w, "No container found for user", http.StatusNotFound)
		return
	}

	//Check if user paid his/her invoice
	invoices, err := cc.invoiceManager.GetUserUnpaidInvoices(authUser.UserID)
	if err != nil {
		//TODO log locally
		sendError(w, "Invoice not found", http.StatusNotFound)
		return
	}
	if len(invoices) > 0 {
		//TODO log locally
		sendError(w, "There are unpaid invoices", http.StatusNotFound)
		return
	}

	// Send message to container
	response, err := cc.containerManager.SendMessage(user.ContainerID, req.Message)
	if err != nil {
		sendError(w, "Failed to process message: "+err.Error(), http.StatusInternalServerError)
		return
	}

	messageResponse := MessageResponse{
		Response:    response,
		ProcessedAt: time.Now(),
		UserID:      authUser.UserID,
		ContainerID: user.ContainerID,
	}

	sendData(w, messageResponse, http.StatusOK)
}

// GetContainerStatus returns the status of the authenticated user's container
// @Summary Get container status
// @Description Returns the status of the user's agent container
// @Tags Container Management
// @Produce json
// @Param Authorization header string true "Bearer token"
// @Success 200 {object} ContainerStatusResponse "Container status"
// @Failure 401 {object} ErrorResponse "Unauthorized"
// @Failure 404 {object} ErrorResponse "Container not found"
// @Router /api/v1/containers/status [get]
func (cc *ContainerController) GetContainerStatus(w http.ResponseWriter, r *http.Request) {
	authUser := GetAuthenticatedUser(r)
	if authUser == nil {
		sendError(w, "Authentication required", http.StatusUnauthorized)
		return
	}

	// Get user's container information
	user, err := cc.userManager.GetUser(authUser.UserID)
	if err != nil {
		sendError(w, "User not found", http.StatusNotFound)
		return
	}

	if user.ContainerID == "" {
		sendError(w, "No container found for user", http.StatusNotFound)
		return
	}

	// Get container information from container manager
	containers, err := cc.containerManager.ListContainers()
	if err != nil {
		sendError(w, "Failed to get container information: "+err.Error(), http.StatusInternalServerError)
		return
	}

	// Find the user's container
	var userContainer *data.ContainerInfo
	for _, container := range containers {
		if container.ID == user.ContainerID {
			userContainer = container
			break
		}
	}

	if userContainer == nil {
		sendError(w, "Container not found", http.StatusNotFound)
		return
	}

	// Check if container is running
	isRunning := cc.containerManager.IsContainerRunning(user.ContainerID)

	response := ContainerStatusResponse{
		ContainerID: userContainer.ID,
		UserID:      userContainer.UserID,
		Status:      userContainer.Status,
		Port:        userContainer.Port,
		Created:     userContainer.Created,
		LastUsed:    userContainer.LastUsed,
		IsRunning:   isRunning,
	}

	sendData(w, response, http.StatusOK)
}

// StartContainer starts the authenticated user's container
// @Summary Start user's container
// @Description Starts the user's agent container if it's stopped
// @Tags Container Management
// @Produce json
// @Param Authorization header string true "Bearer token"
// @Success 200 {object} SuccessResponse "Container started successfully"
// @Failure 401 {object} ErrorResponse "Unauthorized"
// @Failure 404 {object} ErrorResponse "Container not found"
// @Failure 500 {object} ErrorResponse "Failed to start container"
// @Router /api/v1/containers/start [post]
func (cc *ContainerController) StartContainer(w http.ResponseWriter, r *http.Request) {
	authUser := GetAuthenticatedUser(r)
	if authUser == nil {
		sendError(w, "Authentication required", http.StatusUnauthorized)
		return
	}

	// Get user's container ID
	user, err := cc.userManager.GetUser(authUser.UserID)
	if err != nil {
		sendError(w, "User not found", http.StatusNotFound)
		return
	}

	if user.ContainerID == "" {
		sendError(w, "No container found for user", http.StatusNotFound)
		return
	}

	// Start the container
	if err := cc.containerManager.StartContainer(user.ContainerID); err != nil {
		sendError(w, "Failed to start container: "+err.Error(), http.StatusInternalServerError)
		return
	}

	sendSuccess(w, nil, "Container started successfully", http.StatusOK)
}

// StopContainer stops the authenticated user's container
// @Summary Stop user's container
// @Description Stops the user's agent container
// @Tags Container Management
// @Produce json
// @Param Authorization header string true "Bearer token"
// @Success 200 {object} SuccessResponse "Container stopped successfully"
// @Failure 401 {object} ErrorResponse "Unauthorized"
// @Failure 404 {object} ErrorResponse "Container not found"
// @Failure 500 {object} ErrorResponse "Failed to stop container"
// @Router /api/v1/containers/stop [post]
func (cc *ContainerController) StopContainer(w http.ResponseWriter, r *http.Request) {
	authUser := GetAuthenticatedUser(r)
	if authUser == nil {
		sendError(w, "Authentication required", http.StatusUnauthorized)
		return
	}

	// Get user's container ID
	user, err := cc.userManager.GetUser(authUser.UserID)
	if err != nil {
		sendError(w, "User not found", http.StatusNotFound)
		return
	}

	if user.ContainerID == "" {
		sendError(w, "No container found for user", http.StatusNotFound)
		return
	}

	// Stop the container
	if err := cc.containerManager.StopContainer(user.ContainerID); err != nil {
		sendError(w, "Failed to stop container: "+err.Error(), http.StatusInternalServerError)
		return
	}

	sendSuccess(w, nil, "Container stopped successfully", http.StatusOK)
}

// GetContainerByID returns container information by ID (only accessible by the container owner)
// @Summary Get container by ID
// @Description Returns container information by ID (only accessible by the container owner)
// @Tags Container Management
// @Produce json
// @Param containerID path string true "Container ID"
// @Param Authorization header string true "Bearer token"
// @Success 200 {object} ContainerStatusResponse "Container information"
// @Failure 401 {object} ErrorResponse "Unauthorized"
// @Failure 403 {object} ErrorResponse "Access denied"
// @Failure 404 {object} ErrorResponse "Container not found"
// @Router /api/v1/containers/{containerID} [get]
func (cc *ContainerController) GetContainerByID(w http.ResponseWriter, r *http.Request) {
	containerID := chi.URLParam(r, "containerID")
	if containerID == "" {
		sendError(w, "Container ID is required", http.StatusBadRequest)
		return
	}

	authUser := GetAuthenticatedUser(r)
	if authUser == nil {
		sendError(w, "Authentication required", http.StatusUnauthorized)
		return
	}

	// Get user's container ID to ensure they can only access their own container
	user, err := cc.userManager.GetUser(authUser.UserID)
	if err != nil {
		sendError(w, "User not found", http.StatusNotFound)
		return
	}

	// Ensure user can only access their own container
	if user.ContainerID != containerID {
		sendError(w, "Access denied: You can only access your own container", http.StatusForbidden)
		return
	}

	// Get container information
	containers, err := cc.containerManager.ListContainers()
	if err != nil {
		sendError(w, "Failed to get container information: "+err.Error(), http.StatusInternalServerError)
		return
	}

	// Find the requested container
	var targetContainer *data.ContainerInfo
	for _, container := range containers {
		if container.ID == containerID {
			targetContainer = container
			break
		}
	}

	if targetContainer == nil {
		sendError(w, "Container not found", http.StatusNotFound)
		return
	}

	// Check if container is running
	isRunning := cc.containerManager.IsContainerRunning(containerID)

	response := ContainerStatusResponse{
		ContainerID: targetContainer.ID,
		UserID:      targetContainer.UserID,
		Status:      targetContainer.Status,
		Port:        targetContainer.Port,
		Created:     targetContainer.Created,
		LastUsed:    targetContainer.LastUsed,
		IsRunning:   isRunning,
	}

	sendData(w, response, http.StatusOK)
}
