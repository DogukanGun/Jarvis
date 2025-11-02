package controllers

import (
	"context"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"jarvis/api/data"
	"jarvis/api/services"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/google/uuid"
)

// TokenClaims represents the decoded token claims
type TokenClaims struct {
	UserID    string    `json:"user_id"`
	ExpiresAt time.Time `json:"expires_at"`
}

// AuthenticatedUser represents an authenticated user context
type AuthenticatedUser struct {
	User   *data.User
	UserID string
	Token  string
	Claims *TokenClaims
}

// AuthMiddleware validates Bearer token and attaches user to request context
func AuthMiddleware(userManager *services.UserManager) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			// Extract Bearer token from Authorization header
			authHeader := r.Header.Get("Authorization")
			if authHeader == "" {
				sendError(w, "Authorization header required", http.StatusUnauthorized)
				return
			}

			// Check for Bearer token format
			parts := strings.SplitN(authHeader, " ", 2)
			if len(parts) != 2 || parts[0] != "Bearer" {
				sendError(w, "Invalid authorization header format. Use: Bearer <token>", http.StatusUnauthorized)
				return
			}

			token := parts[1]
			if token == "" {
				sendError(w, "Bearer token is required", http.StatusUnauthorized)
				return
			}

			// Decode and validate the token
			claims, err := DecodeToken(token)
			if err != nil {
				sendError(w, "Invalid token: "+err.Error(), http.StatusUnauthorized)
				return
			}

			// Check if token is expired
			if time.Now().After(claims.ExpiresAt) {
				sendError(w, "Token has expired", http.StatusUnauthorized)
				return
			}

			// Validate user exists
			log.Print(claims.UserID)
			user, err := userManager.GetUser(claims.UserID)
			if err != nil {
				sendError(w, "Invalid token or user not found", http.StatusUnauthorized)
				return
			}

			// Update user's last active time
			userManager.UpdateLastActive(claims.UserID)

			// Add authenticated user to request context
			authUser := &AuthenticatedUser{
				User:   user,
				UserID: claims.UserID,
				Token:  token,
				Claims: claims,
			}

			ctx := context.WithValue(r.Context(), "auth_user", authUser)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

// RequireOwnership ensures the authenticated user can only access their own resources
func RequireOwnership() func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			authUser := GetAuthenticatedUser(r)
			if authUser == nil {
				sendError(w, "Authentication required", http.StatusUnauthorized)
				return
			}

			// Get the requested user ID from URL or request
			requestedUserID := getUserIDFromRequest(r)

			// Ensure user can only access their own data
			if authUser.UserID != requestedUserID {
				sendError(w, "Access denied: You can only access your own resources", http.StatusForbidden)
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}

// GetAuthenticatedUser extracts the authenticated user from request context
func GetAuthenticatedUser(r *http.Request) *AuthenticatedUser {
	if authUser, ok := r.Context().Value("auth_user").(*AuthenticatedUser); ok {
		return authUser
	}
	return nil
}

// getUserIDFromRequest extracts user ID from various sources in the request
func getUserIDFromRequest(r *http.Request) string {
	// Try URL parameter first (from chi router)
	if userID := r.URL.Query().Get("user_id"); userID != "" {
		return userID
	}

	// Try from URL path (handled by chi router in specific endpoints)
	// This will be set by individual controllers based on their URL patterns

	return ""
}

// EncodeToken creates a simple base64 encoded token with claims
func EncodeToken(userID string, expirationHours int) (string, error) {
	claims := TokenClaims{
		UserID:    userID,
		ExpiresAt: time.Now().Add(time.Duration(expirationHours) * time.Hour),
	}

	claimsBytes, err := json.Marshal(claims)
	if err != nil {
		return "", err
	}

	// Simple base64 encoding (in production, use proper JWT)
	token := base64.URLEncoding.EncodeToString(claimsBytes)
	return token, nil
}

// DecodeToken decodes a base64 encoded token and returns the claims
func DecodeToken(token string) (*TokenClaims, error) {
	// Decode base64
	claimsBytes, err := base64.URLEncoding.DecodeString(token)
	if err != nil {
		return nil, errors.New("invalid token format")
	}

	// Unmarshal claims
	var claims TokenClaims
	if err := json.Unmarshal(claimsBytes, &claims); err != nil {
		return nil, errors.New("invalid token claims")
	}

	return &claims, nil
}

// WalletAuthRequest represents wallet authentication request
type WalletAuthRequest struct {
	WalletAddress string `json:"wallet_address"`
	Signature     string `json:"signature"`
	Message       string `json:"message"`
	Username      string `json:"username,omitempty"`
	Email         string `json:"email,omitempty"`
}

// WalletAuthResponse represents wallet authentication response
type WalletAuthResponse struct {
	UserID      string    `json:"user_id"`
	Username    string    `json:"username"`
	Email       string    `json:"email"`
	ContainerID string    `json:"container_id"`
	Token       string    `json:"token"`
	CreatedAt   time.Time `json:"created_at"`
	IsNewUser   bool      `json:"is_new_user"`
}

// AuthController handles authentication endpoints
type AuthController struct {
	userManager      *services.UserManager
	containerManager *services.ContainerManager
}

// NewAuthController creates a new auth controller
func NewAuthController(userManager *services.UserManager, containerManager *services.ContainerManager) *AuthController {
	return &AuthController{
		userManager:      userManager,
		containerManager: containerManager,
	}
}

// VerifySignature verifies an Ethereum wallet signature
func VerifySignature(message, signature, walletAddress string) bool {
	// Prepare the message in the Ethereum signed message format
	prefixedMessage := []byte("\x19Ethereum Signed Message:\n" + string(rune(len(message))) + message)
	
	// Hash the prefixed message
	hash := crypto.Keccak256Hash(prefixedMessage)
	
	// Decode the signature
	sig, err := hex.DecodeString(strings.TrimPrefix(signature, "0x"))
	if err != nil {
		log.Printf("Failed to decode signature: %v", err)
		return false
	}
	
	// Ethereum signatures have v as the last byte, and it's either 27 or 28
	// We need to normalize it to 0 or 1
	if len(sig) == 65 {
		if sig[64] >= 27 {
			sig[64] -= 27
		}
	}
	
	// Recover the public key from the signature
	pubKey, err := crypto.SigToPub(hash.Bytes(), sig)
	if err != nil {
		log.Printf("Failed to recover public key: %v", err)
		return false
	}
	
	// Get the address from the public key
	recoveredAddr := crypto.PubkeyToAddress(*pubKey)
	
	// Compare with the provided wallet address
	expectedAddr := common.HexToAddress(walletAddress)
	
	return recoveredAddr == expectedAddr
}

// WalletAuth handles wallet-based authentication (login or signup)
// @Summary Wallet authentication
// @Description Authenticates or creates a user using wallet signature
// @Tags Authentication
// @Accept json
// @Produce json
// @Param request body WalletAuthRequest true "Wallet authentication data"
// @Success 200 {object} WalletAuthResponse "Authentication successful"
// @Failure 400 {object} ErrorResponse "Invalid request"
// @Failure 401 {object} ErrorResponse "Invalid signature"
// @Failure 500 {object} ErrorResponse "Internal server error"
// @Router /api/v1/auth/wallet [post]
func (ac *AuthController) WalletAuth(w http.ResponseWriter, r *http.Request) {
	var req WalletAuthRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		sendError(w, "Invalid JSON payload", http.StatusBadRequest)
		return
	}

	// Validate required fields
	if req.WalletAddress == "" {
		sendError(w, "Wallet address is required", http.StatusBadRequest)
		return
	}
	if req.Signature == "" {
		sendError(w, "Signature is required", http.StatusBadRequest)
		return
	}
	if req.Message == "" {
		sendError(w, "Message is required", http.StatusBadRequest)
		return
	}

	// Verify the signature
	if !VerifySignature(req.Message, req.Signature, req.WalletAddress) {
		sendError(w, "Invalid signature", http.StatusUnauthorized)
		return
	}

	// Normalize wallet address to lowercase
	walletAddress := strings.ToLower(req.WalletAddress)

	// Check if user exists with this wallet address
	user, err := ac.userManager.GetUserByWalletAddress(walletAddress)
	
	isNewUser := false
	
	if err != nil || user == nil {
		// User doesn't exist, create new user
		isNewUser = true
		userID := uuid.New().String()
		
		// Use provided username/email or generate defaults
		username := req.Username
		if username == "" {
			username = "user_" + walletAddress[:8]
		}
		
		email := req.Email
		if email == "" {
			email = walletAddress + "@wallet.local"
		}

		// Create Docker container for the user's agent
		containerID, err := ac.containerManager.CreateContainer(userID)
		if err != nil {
			sendError(w, "Failed to create container: "+err.Error(), http.StatusInternalServerError)
			return
		}

		// Create user
		user = &data.User{
			ID:            userID,
			Username:      username,
			Email:         email,
			Password:      "", // No password for wallet auth
			WalletAddress: walletAddress,
			ContainerID:   containerID,
			CreatedAt:     time.Now(),
			LastActive:    time.Now(),
		}

		if err := ac.userManager.AddUser(user); err != nil {
			sendError(w, "Failed to create user: "+err.Error(), http.StatusInternalServerError)
			return
		}
	} else {
		// User exists, update last active time
		ac.userManager.UpdateLastActive(user.ID)
		
		// Update username/email if provided and different
		updated := false
		if req.Username != "" && req.Username != user.Username {
			user.Username = req.Username
			updated = true
		}
		if req.Email != "" && req.Email != user.Email {
			user.Email = req.Email
			updated = true
		}
		if updated {
			ac.userManager.UpdateUser(user)
		}
	}

	// Generate token for the user (24 hours expiration)
	token, err := EncodeToken(user.ID, 24)
	if err != nil {
		sendError(w, "Failed to generate token: "+err.Error(), http.StatusInternalServerError)
		return
	}

	response := WalletAuthResponse{
		UserID:      user.ID,
		Username:    user.Username,
		Email:       user.Email,
		ContainerID: user.ContainerID,
		Token:       token,
		CreatedAt:   user.CreatedAt,
		IsNewUser:   isNewUser,
	}

	statusCode := http.StatusOK
	if isNewUser {
		statusCode = http.StatusCreated
	}

	sendData(w, response, statusCode)
}

// LogoutRequest represents logout request (can be empty for now)
type LogoutRequest struct{}

// Logout handles user logout
// @Summary Logout user
// @Description Invalidates the user's session (client-side token removal)
// @Tags Authentication
// @Produce json
// @Param Authorization header string true "Bearer token"
// @Success 200 {object} SuccessResponse "Logout successful"
// @Router /api/v1/auth/logout [post]
func (ac *AuthController) Logout(w http.ResponseWriter, r *http.Request) {
	// Since we're using stateless tokens, logout is primarily client-side
	// In a production system, you might want to maintain a token blacklist
	sendSuccess(w, nil, "Logout successful", http.StatusOK)
}
