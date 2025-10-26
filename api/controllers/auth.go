package controllers

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"jarvis/api/data"
	"jarvis/api/services"
	"log"
	"net/http"
	"strings"
	"time"
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
