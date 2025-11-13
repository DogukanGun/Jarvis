package main

import (
	"fmt"
	"os"
	"os/signal"
	"syscall"
)

var globalContainerManager *ContainerManager

func PrepareEnvironmentForCli(userID string) error {
	// Initialize container manager
	globalContainerManager = NewContainerManager(userID)

	// Start the container
	fmt.Println("Starting Jarvis agent container...")
	if err := globalContainerManager.StartContainer(); err != nil {
		return fmt.Errorf("failed to start container: %w", err)
	}

	// Setup signal handlers for cleanup
	setupCleanupHandlers()

	return nil
}

func CleanupEnvironment() {
	if globalContainerManager != nil {
		fmt.Println("Cleaning up container...")
		globalContainerManager.StopContainer()
	}
}

func setupCleanupHandlers() {
	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)

	go func() {
		<-c
		fmt.Println("\nReceived interrupt signal, cleaning up...")
		CleanupEnvironment()
		os.Exit(0)
	}()
}

func GetContainerManager() *ContainerManager {
	return globalContainerManager
}
