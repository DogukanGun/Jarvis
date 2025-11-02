package controllers

import (
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"golang.org/x/crypto/scrypt"
	"jarvis/api/data"
	"jarvis/api/services"
	"net/http"
	"strings"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
)

type UserController struct {
	userManager      *services.UserManager
	containerManager *services.ContainerManager
}

func NewUserController(userManager *services.UserManager, containerManager *services.ContainerManager) *UserController {
	return &UserController{
		userManager:      userManager,
		containerManager: containerManager,
	}
}

// RegisterRequest represents user registration data
type RegisterRequest struct {
	Username      string `json:"username" validate:"required,min=3,max=50"`
	Email         string `json:"email" validate:"required,email"`
	Password      string `json:"password" validate:"required,min=6"`
	WalletAddress string `json:"wallet_address"`
}

// RegisterResponse represents user registration response
type RegisterResponse struct {
	UserID      string    `json:"user_id"`
	Username    string    `json:"username"`
	Email       string    `json:"email"`
	ContainerID string    `json:"container_id"`
	Token       string    `json:"token"`
	CreatedAt   time.Time `json:"created_at"`
}

// UserProfileResponse represents user profile data (without sensitive info)
type UserProfileResponse struct {
	UserID      string    `json:"user_id"`
	Username    string    `json:"username"`
	Email       string    `json:"email"`
	ContainerID string    `json:"container_id"`
	CreatedAt   time.Time `json:"created_at"`
	LastActive  time.Time `json:"last_active"`
	IsActive    bool      `json:"is_active"`
}

// UpdateUserRequest represents user update data
type UpdateUserRequest struct {
	Username string `json:"username,omitempty" validate:"omitempty,min=3,max=50"`
	Email    string `json:"email,omitempty" validate:"omitempty,email"`
}

// LoginRequest represents user login data
type LoginRequest struct {
	Email    string `json:"email" validate:"required,email"`
	Password string `json:"password" validate:"required"`
}

// LoginResponse represents user login response
type LoginResponse struct {
	UserID      string    `json:"user_id"`
	Username    string    `json:"username"`
	Email       string    `json:"email"`
	ContainerID string    `json:"container_id"`
	Token       string    `json:"token"`
	LastActive  time.Time `json:"last_active"`
}

// hashPassword creates a hashed password using scrypt
func hashPassword(password string) (string, error) {
	salt := make([]byte, 32)
	_, err := rand.Read(salt)
	if err != nil {
		return "", err
	}

	dk, err := scrypt.Key([]byte(password), salt, 32768, 8, 1, 32)
	if err != nil {
		return "", err
	}

	return base64.StdEncoding.EncodeToString(salt) + ":" + base64.StdEncoding.EncodeToString(dk), nil
}

// verifyPassword verifies a password against its hash
func verifyPassword(password, hash string) bool {
	// Split the hash into salt and key parts
	parts := strings.Split(hash, ":")
	if len(parts) != 2 {
		return false
	}

	salt, err := base64.StdEncoding.DecodeString(parts[0])
	if err != nil {
		return false
	}

	storedKey, err := base64.StdEncoding.DecodeString(parts[1])
	if err != nil {
		return false
	}

	dk, err := scrypt.Key([]byte(password), salt, 32768, 8, 1, 32)
	if err != nil {
		return false
	}

	// Compare the derived key with the stored key
	if len(dk) != len(storedKey) {
		return false
	}

	for i := range dk {
		if dk[i] != storedKey[i] {
			return false
		}
	}

	return true
}

// RegisterUser creates a new user and spawns their agent container
// @Summary Register a new user
// @Description Creates a new user account and spins up a dedicated Docker container with a Jarvis agent instance
// @Tags User Management
// @Accept json
// @Produce json
// @Param request body RegisterRequest true "User registration data"
// @Success 201 {object} RegisterResponse "User registered successfully"
// @Failure 400 {object} ErrorResponse "Invalid request body"
// @Failure 409 {object} ErrorResponse "User already exists"
// @Failure 500 {object} ErrorResponse "Internal server error"
// @Router /api/v1/users/register [post]
func (uc *UserController) RegisterUser(w http.ResponseWriter, r *http.Request) {
	var req RegisterRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		sendError(w, "Invalid JSON payload", http.StatusBadRequest)
		return
	}

	// Validate required fields
	if req.Username == "" {
		sendError(w, "Username is required", http.StatusBadRequest)
		return
	}
	if req.Email == "" {
		sendError(w, "Email is required", http.StatusBadRequest)
		return
	}
	if req.Password == "" {
		sendError(w, "Password is required", http.StatusBadRequest)
		return
	}
	if len(req.Password) < 6 {
		sendError(w, "Password must be at least 6 characters long", http.StatusBadRequest)
		return
	}
	if req.WalletAddress == "" {
		sendError(w, "WalletAddress is required", http.StatusBadRequest)
		return
	}

	// Check if user already exists
	if uc.userManager.UserExists(req.Username) {
		sendError(w, "User already exists", http.StatusConflict)
		return
	}

	// Check if email already exists
	if existingUser, _ := uc.userManager.GetUserByEmail(req.Email); existingUser != nil {
		sendError(w, "Email already registered", http.StatusConflict)
		return
	}

	// Hash the password
	hashedPassword, err := hashPassword(req.Password)
	if err != nil {
		sendError(w, "Failed to process password", http.StatusInternalServerError)
		return
	}

	// Generate user ID
	userID := uuid.New().String()

	// Create user
	user := &data.User{
		ID:            userID,
		Username:      req.Username,
		Email:         req.Email,
		Password:      hashedPassword,
		WalletAddress: req.WalletAddress,
		CreatedAt:     time.Now(),
	}

	// Create Docker container for the user's agent
	containerID, err := uc.containerManager.CreateContainer(userID)
	if err != nil {
		sendError(w, "Failed to create container: "+err.Error(), http.StatusInternalServerError)
		return
	}

	// Store user with container ID
	user.ContainerID = containerID
	if err := uc.userManager.AddUser(user); err != nil {
		sendError(w, "Failed to create user: "+err.Error(), http.StatusInternalServerError)
		return
	}

	// Generate token for the user (24 hours expiration)
	token, err := EncodeToken(userID, 24)
	if err != nil {
		sendError(w, "Failed to generate token: "+err.Error(), http.StatusInternalServerError)
		return
	}

	response := RegisterResponse{
		UserID:      userID,
		Username:    req.Username,
		Email:       req.Email,
		ContainerID: containerID,
		Token:       token,
		CreatedAt:   user.CreatedAt,
	}

	sendData(w, response, http.StatusCreated)
}

// GetUserProfile returns the authenticated user's profile information
// @Summary Get user profile
// @Description Returns the authenticated user's profile information
// @Tags User Management
// @Produce json
// @Param Authorization header string true "Bearer token"
// @Success 200 {object} UserProfileResponse "User profile"
// @Failure 401 {object} ErrorResponse "Unauthorized"
// @Failure 404 {object} ErrorResponse "User not found"
// @Router /api/v1/users/profile [get]
func (uc *UserController) GetUserProfile(w http.ResponseWriter, r *http.Request) {
	authUser := GetAuthenticatedUser(r)
	if authUser == nil {
		sendError(w, "Authentication required", http.StatusUnauthorized)
		return
	}

	// Get fresh user data from database
	user, err := uc.userManager.GetUser(authUser.UserID)
	if err != nil {
		sendError(w, "User not found", http.StatusNotFound)
		return
	}

	// Check if container is running
	isActive := false
	if user.ContainerID != "" {
		isActive = uc.containerManager.IsContainerRunning(user.ContainerID)
	}

	response := UserProfileResponse{
		UserID:      user.ID,
		Username:    user.Username,
		Email:       user.Email,
		ContainerID: user.ContainerID,
		CreatedAt:   user.CreatedAt,
		LastActive:  user.LastActive,
		IsActive:    isActive,
	}

	sendData(w, response, http.StatusOK)
}

// GetUserByID returns user information by ID (only accessible by the user themselves)
// @Summary Get user by ID
// @Description Returns user information by ID (only accessible by the user themselves)
// @Tags User Management
// @Produce json
// @Param userID path string true "User ID"
// @Param Authorization header string true "Bearer token"
// @Success 200 {object} UserProfileResponse "User information"
// @Failure 401 {object} ErrorResponse "Unauthorized"
// @Failure 403 {object} ErrorResponse "Access denied"
// @Failure 404 {object} ErrorResponse "User not found"
// @Router /api/v1/users/{userID} [get]
func (uc *UserController) GetUserByID(w http.ResponseWriter, r *http.Request) {
	userID := chi.URLParam(r, "userID")
	if userID == "" {
		sendError(w, "User ID is required", http.StatusBadRequest)
		return
	}

	authUser := GetAuthenticatedUser(r)
	if authUser == nil {
		sendError(w, "Authentication required", http.StatusUnauthorized)
		return
	}

	// Ensure user can only access their own data
	if authUser.UserID != userID {
		sendError(w, "Access denied: You can only access your own profile", http.StatusForbidden)
		return
	}

	user, err := uc.userManager.GetUser(userID)
	if err != nil {
		sendError(w, "User not found", http.StatusNotFound)
		return
	}

	// Check if container is running
	isActive := false
	if user.ContainerID != "" {
		isActive = uc.containerManager.IsContainerRunning(user.ContainerID)
	}

	response := UserProfileResponse{
		UserID:      user.ID,
		Username:    user.Username,
		Email:       user.Email,
		ContainerID: user.ContainerID,
		CreatedAt:   user.CreatedAt,
		LastActive:  user.LastActive,
		IsActive:    isActive,
	}

	sendData(w, response, http.StatusOK)
}

// UpdateUser updates the authenticated user's information
// @Summary Update user information
// @Description Updates the authenticated user's profile information
// @Tags User Management
// @Accept json
// @Produce json
// @Param userID path string true "User ID"
// @Param request body UpdateUserRequest true "Updated user data"
// @Param Authorization header string true "Bearer token"
// @Success 200 {object} UserProfileResponse "Updated user information"
// @Failure 400 {object} ErrorResponse "Invalid request"
// @Failure 401 {object} ErrorResponse "Unauthorized"
// @Failure 403 {object} ErrorResponse "Access denied"
// @Failure 404 {object} ErrorResponse "User not found"
// @Router /api/v1/users/{userID} [put]
func (uc *UserController) UpdateUser(w http.ResponseWriter, r *http.Request) {
	userID := chi.URLParam(r, "userID")
	if userID == "" {
		sendError(w, "User ID is required", http.StatusBadRequest)
		return
	}

	authUser := GetAuthenticatedUser(r)
	if authUser == nil {
		sendError(w, "Authentication required", http.StatusUnauthorized)
		return
	}

	// Ensure user can only update their own data
	if authUser.UserID != userID {
		sendError(w, "Access denied: You can only update your own profile", http.StatusForbidden)
		return
	}

	var req UpdateUserRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		sendError(w, "Invalid JSON payload", http.StatusBadRequest)
		return
	}

	// Get current user data
	user, err := uc.userManager.GetUser(userID)
	if err != nil {
		sendError(w, "User not found", http.StatusNotFound)
		return
	}

	// Update fields if provided
	if req.Username != "" {
		// Check if username is already taken by another user
		if existingUser, _ := uc.userManager.GetUserByUsername(req.Username); existingUser != nil && existingUser.ID != userID {
			sendError(w, "Username already taken", http.StatusConflict)
			return
		}
		user.Username = req.Username
	}

	if req.Email != "" {
		// Check if email is already taken by another user
		if existingUser, _ := uc.userManager.GetUserByEmail(req.Email); existingUser != nil && existingUser.ID != userID {
			sendError(w, "Email already registered", http.StatusConflict)
			return
		}
		user.Email = req.Email
	}

	// Update user in database
	if err := uc.userManager.UpdateUser(user); err != nil {
		sendError(w, "Failed to update user: "+err.Error(), http.StatusInternalServerError)
		return
	}

	// Check if container is running
	isActive := false
	if user.ContainerID != "" {
		isActive = uc.containerManager.IsContainerRunning(user.ContainerID)
	}

	response := UserProfileResponse{
		UserID:      user.ID,
		Username:    user.Username,
		Email:       user.Email,
		ContainerID: user.ContainerID,
		CreatedAt:   user.CreatedAt,
		LastActive:  user.LastActive,
		IsActive:    isActive,
	}

	sendData(w, response, http.StatusOK)
}

// DeleteUser deletes the authenticated user's account
// @Summary Delete user account
// @Description Deletes the authenticated user's account and associated container
// @Tags User Management
// @Produce json
// @Param userID path string true "User ID"
// @Param Authorization header string true "Bearer token"
// @Success 200 {object} SuccessResponse "User deleted successfully"
// @Failure 401 {object} ErrorResponse "Unauthorized"
// @Failure 403 {object} ErrorResponse "Access denied"
// @Failure 404 {object} ErrorResponse "User not found"
// @Router /api/v1/users/{userID} [delete]
func (uc *UserController) DeleteUser(w http.ResponseWriter, r *http.Request) {
	userID := chi.URLParam(r, "userID")
	if userID == "" {
		sendError(w, "User ID is required", http.StatusBadRequest)
		return
	}

	authUser := GetAuthenticatedUser(r)
	if authUser == nil {
		sendError(w, "Authentication required", http.StatusUnauthorized)
		return
	}

	// Ensure user can only delete their own account
	if authUser.UserID != userID {
		sendError(w, "Access denied: You can only delete your own account", http.StatusForbidden)
		return
	}

	// Get user to find container ID
	user, err := uc.userManager.GetUser(userID)
	if err != nil {
		sendError(w, "User not found", http.StatusNotFound)
		return
	}

	// Stop and remove user's container if it exists
	if user.ContainerID != "" {
		uc.containerManager.StopContainer(user.ContainerID)
		// Note: Container cleanup could be improved with proper cleanup method
	}

	// Delete user from database
	if err := uc.userManager.RemoveUser(userID); err != nil {
		sendError(w, "Failed to delete user: "+err.Error(), http.StatusInternalServerError)
		return
	}

	sendSuccess(w, nil, "User account deleted successfully", http.StatusOK)
}

// LoginUser authenticates a user and returns a token
// @Summary Login user
// @Description Authenticates a user with email and password, returns a token
// @Tags Authentication
// @Accept json
// @Produce json
// @Param request body LoginRequest true "User login credentials"
// @Success 200 {object} LoginResponse "Login successful"
// @Failure 400 {object} ErrorResponse "Invalid request body"
// @Failure 401 {object} ErrorResponse "Invalid credentials"
// @Failure 404 {object} ErrorResponse "User not found"
// @Router /api/v1/users/login [post]
func (uc *UserController) LoginUser(w http.ResponseWriter, r *http.Request) {
	var req LoginRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		sendError(w, "Invalid JSON payload", http.StatusBadRequest)
		return
	}

	// Validate required fields
	if req.Email == "" {
		sendError(w, "Email is required", http.StatusBadRequest)
		return
	}
	if req.Password == "" {
		sendError(w, "Password is required", http.StatusBadRequest)
		return
	}

	// Find user by email
	user, err := uc.userManager.GetUserByEmail(req.Email)
	if err != nil || user == nil {
		sendError(w, "Invalid email or password", http.StatusUnauthorized)
		return
	}

	// Verify password
	if !verifyPassword(req.Password, user.Password) {
		sendError(w, "Invalid email or password", http.StatusUnauthorized)
		return
	}

	// Update user's last active time
	uc.userManager.UpdateLastActive(user.ID)

	// Generate token for the user (24 hours expiration)
	token, err := EncodeToken(user.ID, 24)
	if err != nil {
		sendError(w, "Failed to generate token: "+err.Error(), http.StatusInternalServerError)
		return
	}

	response := LoginResponse{
		UserID:      user.ID,
		Username:    user.Username,
		Email:       user.Email,
		ContainerID: user.ContainerID,
		Token:       token,
		LastActive:  user.LastActive,
	}

	sendData(w, response, http.StatusOK)
}
