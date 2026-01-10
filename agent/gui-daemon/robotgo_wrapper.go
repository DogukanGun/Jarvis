package main

import (
	"bytes"
	"fmt"
	"image"
	"image/png"
	"log"
	"os/exec"
	"runtime"
	"strings"
	"time"

	"github.com/go-vgo/robotgo"
	hook "github.com/robotn/gohook"
	"github.com/vcaesar/bitmap"
)

// RobotGoService wraps RobotGo library for GUI automation
type RobotGoService struct {
	autoDelayMs int
}

// NewRobotGoService creates a new RobotGo service
func NewRobotGoService() *RobotGoService {
	return &RobotGoService{
		autoDelayMs: 100, // Default delay between actions
	}
}

// MouseMove moves cursor to coordinates
func (r *RobotGoService) MouseMove(x, y int) error {
	log.Printf("Moving mouse to coordinates: (%d, %d)", x, y)
	robotgo.Move(x, y)
	time.Sleep(time.Duration(r.autoDelayMs) * time.Millisecond)
	return nil
}

// MouseClick clicks mouse button
func (r *RobotGoService) MouseClick(button ButtonType) error {
	log.Printf("Clicking mouse button: %s", button)

	buttonStr := string(button)
	if button == ButtonMiddle {
		buttonStr = "center" // RobotGo uses "center" instead of "middle"
	}

	robotgo.Click(buttonStr, false) // false = single click
	time.Sleep(time.Duration(r.autoDelayMs) * time.Millisecond)
	return nil
}

// MouseDoubleClick performs double click
func (r *RobotGoService) MouseDoubleClick(button ButtonType) error {
	log.Printf("Double-clicking mouse button: %s", button)

	buttonStr := string(button)
	if button == ButtonMiddle {
		buttonStr = "center"
	}

	robotgo.Click(buttonStr, true) // true = double click
	time.Sleep(time.Duration(r.autoDelayMs) * time.Millisecond)
	return nil
}

// MouseToggle presses or releases mouse button
func (r *RobotGoService) MouseToggle(button ButtonType, down bool) error {
	action := "up"
	if down {
		action = "down"
	}
	log.Printf("Mouse button %s: %s", button, action)

	buttonStr := string(button)
	if button == ButtonMiddle {
		buttonStr = "center"
	}

	robotgo.Toggle(buttonStr, action)
	time.Sleep(time.Duration(r.autoDelayMs) * time.Millisecond)
	return nil
}

// MouseScroll scrolls in a direction
func (r *RobotGoService) MouseScroll(direction ScrollDirection, amount int) error {
	log.Printf("Scrolling %s by %d", direction, amount)

	x := 0
	y := 0

	switch direction {
	case ScrollUp:
		y = amount
	case ScrollDown:
		y = -amount
	case ScrollLeft:
		x = -amount
	case ScrollRight:
		x = amount
	}

	robotgo.Scroll(x, y)
	time.Sleep(time.Duration(r.autoDelayMs) * time.Millisecond)
	return nil
}

// GetCursorPosition returns current cursor position
func (r *RobotGoService) GetCursorPosition() (int, int, error) {
	x, y := robotgo.GetMousePos()
	log.Printf("Cursor position: (%d, %d)", x, y)
	return x, y, nil
}

// TypeText types text character by character
func (r *RobotGoService) TypeText(text string, delayMs int) error {
	log.Printf("Typing text: %s", text)

	for _, char := range text {
		robotgo.TypeStr(string(char))
		if delayMs > 0 {
			time.Sleep(time.Duration(delayMs) * time.Millisecond)
		}
	}

	return nil
}

// TypeString types entire string at once (faster)
func (r *RobotGoService) TypeString(text string) error {
	log.Printf("Typing string: %s", text)
	robotgo.TypeStr(text)
	time.Sleep(time.Duration(r.autoDelayMs) * time.Millisecond)
	return nil
}

// PressKey presses and releases a key
func (r *RobotGoService) PressKey(keys ...string) error {
	log.Printf("Pressing keys: %v", keys)

	if len(keys) == 1 {
		robotgo.KeyTap(keys[0])
	} else if len(keys) > 1 {
		// First key is the main key, rest are modifiers
		modifiers := keys[:len(keys)-1]
		mainKey := keys[len(keys)-1]
		robotgo.KeyTap(mainKey, modifiers)
	}

	time.Sleep(time.Duration(r.autoDelayMs) * time.Millisecond)
	return nil
}

// KeyToggle presses or releases a key
func (r *RobotGoService) KeyToggle(key string, down bool) error {
	action := "up"
	if down {
		action = "down"
	}
	log.Printf("Key %s: %s", key, action)

	robotgo.KeyToggle(key, action)
	time.Sleep(time.Duration(r.autoDelayMs) * time.Millisecond)
	return nil
}

// PasteText pastes text using clipboard
func (r *RobotGoService) PasteText(text string) error {
	log.Printf("Pasting text (length: %d)", len(text))

	// Write to clipboard
	err := robotgo.WriteAll(text)
	if err != nil {
		return fmt.Errorf("failed to write to clipboard: %v", err)
	}

	// Brief pause to ensure clipboard is set
	time.Sleep(100 * time.Millisecond)

	// Paste using Ctrl+V (Cmd+V on macOS)
	if runtime.GOOS == "darwin" {
		robotgo.KeyTap("v", "cmd")
	} else {
		robotgo.KeyTap("v", "ctrl")
	}

	time.Sleep(time.Duration(r.autoDelayMs) * time.Millisecond)
	return nil
}

// CaptureScreen captures screenshot and returns image
func (r *RobotGoService) CaptureScreen() (image.Image, error) {
	log.Println("Capturing screen")

	bmp := robotgo.CaptureScreen()
	if bmp == nil {
		return nil, fmt.Errorf("failed to capture screen")
	}

	defer robotgo.FreeBitmap(bmp)

	img := robotgo.ToImage(bmp)
	return img, nil
}

// CaptureScreenPNG captures screenshot and returns PNG bytes
func (r *RobotGoService) CaptureScreenPNG() ([]byte, error) {
	img, err := r.CaptureScreen()
	if err != nil {
		return nil, err
	}

	// Convert to PNG
	var buf bytes.Buffer
	err = png.Encode(&buf, img)
	if err != nil {
		return nil, fmt.Errorf("failed to encode PNG: %v", err)
	}

	return buf.Bytes(), nil
}

// GetScreenSize returns screen dimensions
func (r *RobotGoService) GetScreenSize() (int, int) {
	width, height := robotgo.GetScreenSize()
	return width, height
}

// FindImage finds an image on screen
func (r *RobotGoService) FindImage(imagePath string) (int, int, error) {
	log.Printf("Finding image on screen: %s", imagePath)

	// Capture the entire screen
	bit := robotgo.CaptureScreen()
	if bit == nil {
		return 0, 0, fmt.Errorf("failed to capture screen")
	}
	defer robotgo.FreeBitmap(bit)

	// Find the image on screen with default tolerance (0.0 = exact match)
	x, y := bitmap.FindPic(imagePath, bit)

	if x == -1 || y == -1 {
		return 0, 0, fmt.Errorf("image not found on screen: %s", imagePath)
	}

	log.Printf("Image found at position: (%d, %d)", x, y)
	return x, y, nil
}

// GetPixelColor gets color at specific coordinates
func (r *RobotGoService) GetPixelColor(x, y int) string {
	hex := robotgo.GetPixelColor(x, y)
	return hex
}

// Delay waits for specified milliseconds
func (r *RobotGoService) Delay(ms int) {
	log.Printf("Waiting for %d ms", ms)
	time.Sleep(time.Duration(ms) * time.Millisecond)
}

// ExecuteCommand executes shell command (for application launching)
func (r *RobotGoService) ExecuteCommand(command string, args ...string) error {
	log.Printf("Executing command: %s %v", command, args)

	cmd := exec.Command(command, args...)
	err := cmd.Start()
	if err != nil {
		return fmt.Errorf("failed to execute command: %v", err)
	}

	// Don't wait for command to finish (detached execution)
	go func() {
		if err := cmd.Wait(); err != nil {
			log.Printf("Command finished with error: %v", err)
		}
	}()

	return nil
}

// ActivateWindow activates a window by title
func (r *RobotGoService) ActivateWindow(title string) error {
	log.Printf("Activating window: %s", title)

	pids, err := robotgo.Pids()
	if err != nil {
		return fmt.Errorf("failed to get process list: %v", err)
	}

	for _, pid := range pids {
		windowTitle := robotgo.GetTitle(pid)
		if len(windowTitle) > 0 && len(title) > 0 {
			// Check if window title contains the search title (case-insensitive)
			titleLower := strings.ToLower(title)
			windowTitleLower := strings.ToLower(windowTitle)
			if strings.Contains(windowTitleLower, titleLower) {
				if err := robotgo.ActivePid(pid); err != nil {
					log.Printf("Warning: failed to activate window: %v", err)
					continue
				}
				return nil
			}
		}
	}
	return fmt.Errorf("window not found: %s", title)
}

// AddEvent adds global event listener (for future use)
func (r *RobotGoService) AddEvent(eventType string) chan hook.Event {
	log.Printf("Adding event listener: %s", eventType)
	evChan := hook.Start()
	return evChan
}

// RemoveEvent removes event listener
func (r *RobotGoService) RemoveEvent() {
	log.Println("Removing event listener")
	hook.End()
}
