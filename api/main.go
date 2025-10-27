package main

import (
	"fmt"
	"log"
	"net/http"
	"os"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	httpSwagger "github.com/swaggo/http-swagger"

	"jarvis/api/controllers"
	_ "jarvis/api/docs" // Import generated swagger docs
	"jarvis/api/repository"
	"jarvis/api/services"
)

func main() {
	r := chi.NewRouter()

	// Middleware
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)

	// CORS middleware for web clients
	r.Use(func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Access-Control-Allow-Origin", "*")
			w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
			w.Header().Set("Access-Control-Allow-Headers", "Accept, Authorization, Content-Type, X-CSRF-Token")
			if r.Method == "OPTIONS" {
				return
			}
			next.ServeHTTP(w, r)
		})
	})

	// Initialize database
	database, err := NewDatabase()
	if err != nil {
		log.Fatal("Failed to connect to database:", err)
	}
	defer database.Close()

	// Initialize repositories
	userRepo := repository.NewUserRepository(database.GetDatabase())
	containerRepo := repository.NewContainerRepository(database.GetDatabase())

	// Initialize services
	userManager := services.NewUserManager(userRepo)
	containerManager := services.NewContainerManager(containerRepo)

	// Initialize controllers
	userController := controllers.NewUserController(userManager, containerManager)
	containerController := controllers.NewContainerController(containerManager, userManager)

	// Initialize auth middleware
	authMiddleware := controllers.AuthMiddleware(userManager)

	// Swagger documentation
	var swaggerURL string
	if os.Getenv("OS") == "dev" {
		swaggerURL = "http://localhost:8080/swagger/doc.json"
	} else {
		swaggerURL = "https://jarvis.dogukangun.com/swagger/doc.json"
	}
	r.Get("/swagger/*", httpSwagger.Handler(
		httpSwagger.URL(swaggerURL),
	))

	// Health check (public endpoint)
	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"status":"healthy","service":"jarvis-api","version":"1.0.0"}`))
	})

	// API routes
	r.Route("/api/v1", func(r chi.Router) {
		// Public routes (no authentication required)
		r.Group(func(r chi.Router) {
			// User registration and login
			r.Post("/users/register", userController.RegisterUser)
			r.Post("/users/login", userController.LoginUser)
		})

		// Protected routes (authentication required)
		r.Group(func(r chi.Router) {
			// Apply authentication middleware
			r.Use(authMiddleware)

			// User routes
			r.Get("/users/profile", userController.GetUserProfile)
			r.Get("/users/{userID}", userController.GetUserByID)
			r.Put("/users/{userID}", userController.UpdateUser)
			r.Delete("/users/{userID}", userController.DeleteUser)

			// Container routes
			r.Post("/containers/message", containerController.SendMessage)
			r.Get("/containers/status", containerController.GetContainerStatus)
			r.Post("/containers/start", containerController.StartContainer)
			r.Post("/containers/stop", containerController.StopContainer)
			r.Get("/containers/{containerID}", containerController.GetContainerByID)
		})
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	fmt.Printf("Jarvis API Server starting on port %s\n", port)
	fmt.Printf("Available endpoints:\n")
	fmt.Printf("Public endpoints:\n")
	fmt.Printf("  GET  /health                        - Health check\n")
	fmt.Printf("  POST /api/v1/users/register         - Register new user and create agent container\n")
	fmt.Printf("  POST /api/v1/users/login            - Login with email and password\n")
	fmt.Printf("  GET  /swagger/*                     - Swagger API documentation\n")
	fmt.Printf("\nProtected endpoints (require Bearer token):\n")
	fmt.Printf("  GET  /api/v1/users/profile          - Get authenticated user's profile\n")
	fmt.Printf("  GET  /api/v1/users/{userID}         - Get user by ID (own only)\n")
	fmt.Printf("  PUT  /api/v1/users/{userID}         - Update user (own only)\n")
	fmt.Printf("  DELETE /api/v1/users/{userID}       - Delete user (own only)\n")
	fmt.Printf("  POST /api/v1/containers/message     - Send message to user's agent\n")
	fmt.Printf("  GET  /api/v1/containers/status      - Get container status\n")
	fmt.Printf("  POST /api/v1/containers/start       - Start user's container\n")
	fmt.Printf("  POST /api/v1/containers/stop        - Stop user's container\n")
	fmt.Printf("  GET  /api/v1/containers/{id}        - Get container by ID (own only)\n")

	log.Fatal(http.ListenAndServe(":"+port, r))
}
