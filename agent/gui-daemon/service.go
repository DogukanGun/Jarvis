package main

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"os"
	_ "os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

// ComputerUseService handles computer automation actions
type ComputerUseService struct {
	robotGo *RobotGoService
}

// NewComputerUseService creates a new service instance
func NewComputerUseService() *ComputerUseService {
	return &ComputerUseService{
		robotGo: NewRobotGoService(),
	}
}

// ExecuteAction executes a computer action based on type
func (s *ComputerUseService) ExecuteAction(action ComputerAction) (interface{}, error) {
	log.Printf("Executing computer action: %s", action.Action)

	switch action.Action {
	case "move_mouse":
		return s.moveMouse(action.Data)
	case "trace_mouse":
		return s.traceMouse(action.Data)
	case "click_mouse":
		return s.clickMouse(action.Data)
	case "press_mouse":
		return s.pressMouse(action.Data)
	case "drag_mouse":
		return s.dragMouse(action.Data)
	case "scroll":
		return s.scroll(action.Data)
	case "type_keys":
		return s.typeKeys(action.Data)
	case "press_keys":
		return s.pressKeys(action.Data)
	case "type_text":
		return s.typeText(action.Data)
	case "paste_text":
		return s.pasteText(action.Data)
	case "wait":
		return s.wait(action.Data)
	case "screenshot":
		return s.screenshot(action.Data)
	case "cursor_position":
		return s.cursorPosition(action.Data)
	case "application":
		return s.application(action.Data)
	case "write_file":
		return s.writeFile(action.Data)
	case "read_file":
		return s.readFile(action.Data)
	default:
		return nil, fmt.Errorf("unsupported action: %s", action.Action)
	}
}

// moveMouse moves cursor to coordinates
func (s *ComputerUseService) moveMouse(data json.RawMessage) (interface{}, error) {
	var params MoveMouseAction
	if err := json.Unmarshal(data, &params); err != nil {
		return nil, err
	}

	return nil, s.robotGo.MouseMove(params.Coordinates.X, params.Coordinates.Y)
}

// traceMouse moves mouse along a path
func (s *ComputerUseService) traceMouse(data json.RawMessage) (interface{}, error) {
	var params TraceMouseAction
	if err := json.Unmarshal(data, &params); err != nil {
		return nil, err
	}

	// Move to first coordinate
	if len(params.Path) == 0 {
		return nil, fmt.Errorf("path is empty")
	}

	if err := s.robotGo.MouseMove(params.Path[0].X, params.Path[0].Y); err != nil {
		return nil, err
	}

	// Hold keys if provided
	if len(params.HoldKeys) > 0 {
		for _, key := range params.HoldKeys {
			if err := s.robotGo.KeyToggle(key, true); err != nil {
				return nil, err
			}
		}
	}

	// Move along path
	for _, coord := range params.Path {
		if err := s.robotGo.MouseMove(coord.X, coord.Y); err != nil {
			return nil, err
		}
	}

	// Release keys
	if len(params.HoldKeys) > 0 {
		for _, key := range params.HoldKeys {
			if err := s.robotGo.KeyToggle(key, false); err != nil {
				return nil, err
			}
		}
	}

	return nil, nil
}

// clickMouse performs mouse click
func (s *ComputerUseService) clickMouse(data json.RawMessage) (interface{}, error) {
	var params ClickMouseAction
	if err := json.Unmarshal(data, &params); err != nil {
		return nil, err
	}

	// Move to coordinates if provided
	if params.Coordinates != nil {
		if err := s.robotGo.MouseMove(params.Coordinates.X, params.Coordinates.Y); err != nil {
			return nil, err
		}
	}

	// Hold keys if provided
	if len(params.HoldKeys) > 0 {
		for _, key := range params.HoldKeys {
			if err := s.robotGo.KeyToggle(key, true); err != nil {
				return nil, err
			}
		}
	}

	// Perform clicks
	if params.ClickCount > 1 {
		for i := 0; i < params.ClickCount; i++ {
			if err := s.robotGo.MouseClick(params.Button); err != nil {
				return nil, err
			}
			time.Sleep(150 * time.Millisecond)
		}
	} else {
		if err := s.robotGo.MouseClick(params.Button); err != nil {
			return nil, err
		}
	}

	// Release keys
	if len(params.HoldKeys) > 0 {
		for _, key := range params.HoldKeys {
			if err := s.robotGo.KeyToggle(key, false); err != nil {
				return nil, err
			}
		}
	}

	return nil, nil
}

// pressMouse presses or releases mouse button
func (s *ComputerUseService) pressMouse(data json.RawMessage) (interface{}, error) {
	var params PressMouseAction
	if err := json.Unmarshal(data, &params); err != nil {
		return nil, err
	}

	// Move to coordinates if provided
	if params.Coordinates != nil {
		if err := s.robotGo.MouseMove(params.Coordinates.X, params.Coordinates.Y); err != nil {
			return nil, err
		}
	}

	down := params.Press == PressDown
	return nil, s.robotGo.MouseToggle(params.Button, down)
}

// dragMouse drags mouse along a path
func (s *ComputerUseService) dragMouse(data json.RawMessage) (interface{}, error) {
	var params DragMouseAction
	if err := json.Unmarshal(data, &params); err != nil {
		return nil, err
	}

	if len(params.Path) == 0 {
		return nil, fmt.Errorf("path is empty")
	}

	// Move to first coordinate
	if err := s.robotGo.MouseMove(params.Path[0].X, params.Path[0].Y); err != nil {
		return nil, err
	}

	// Hold keys if provided
	if len(params.HoldKeys) > 0 {
		for _, key := range params.HoldKeys {
			if err := s.robotGo.KeyToggle(key, true); err != nil {
				return nil, err
			}
		}
	}

	// Press mouse button
	if err := s.robotGo.MouseToggle(params.Button, true); err != nil {
		return nil, err
	}

	// Drag along path
	for _, coord := range params.Path {
		if err := s.robotGo.MouseMove(coord.X, coord.Y); err != nil {
			return nil, err
		}
	}

	// Release mouse button
	if err := s.robotGo.MouseToggle(params.Button, false); err != nil {
		return nil, err
	}

	// Release keys
	if len(params.HoldKeys) > 0 {
		for _, key := range params.HoldKeys {
			if err := s.robotGo.KeyToggle(key, false); err != nil {
				return nil, err
			}
		}
	}

	return nil, nil
}

// scroll performs scroll operation
func (s *ComputerUseService) scroll(data json.RawMessage) (interface{}, error) {
	var params ScrollAction
	if err := json.Unmarshal(data, &params); err != nil {
		return nil, err
	}

	// Move to coordinates if provided
	if params.Coordinates != nil {
		if err := s.robotGo.MouseMove(params.Coordinates.X, params.Coordinates.Y); err != nil {
			return nil, err
		}
	}

	// Hold keys if provided
	if len(params.HoldKeys) > 0 {
		for _, key := range params.HoldKeys {
			if err := s.robotGo.KeyToggle(key, true); err != nil {
				return nil, err
			}
		}
	}

	// Perform scroll
	for i := 0; i < params.ScrollCount; i++ {
		if err := s.robotGo.MouseScroll(params.Direction, 1); err != nil {
			return nil, err
		}
		time.Sleep(150 * time.Millisecond)
	}

	// Release keys
	if len(params.HoldKeys) > 0 {
		for _, key := range params.HoldKeys {
			if err := s.robotGo.KeyToggle(key, false); err != nil {
				return nil, err
			}
		}
	}

	return nil, nil
}

// typeKeys types key combination
func (s *ComputerUseService) typeKeys(data json.RawMessage) (interface{}, error) {
	var params TypeKeysAction
	if err := json.Unmarshal(data, &params); err != nil {
		return nil, err
	}

	if len(params.Keys) == 0 {
		return nil, fmt.Errorf("keys array is empty")
	}

	// Press all keys
	for _, key := range params.Keys {
		if err := s.robotGo.KeyToggle(key, true); err != nil {
			return nil, err
		}
	}

	// Delay if specified
	if params.Delay > 0 {
		time.Sleep(time.Duration(params.Delay) * time.Millisecond)
	} else {
		time.Sleep(100 * time.Millisecond)
	}

	// Release all keys in reverse order
	for i := len(params.Keys) - 1; i >= 0; i-- {
		if err := s.robotGo.KeyToggle(params.Keys[i], false); err != nil {
			return nil, err
		}
	}

	return nil, nil
}

// pressKeys holds or releases keys
func (s *ComputerUseService) pressKeys(data json.RawMessage) (interface{}, error) {
	var params PressKeysAction
	if err := json.Unmarshal(data, &params); err != nil {
		return nil, err
	}

	down := params.Press == PressDown

	for _, key := range params.Keys {
		if err := s.robotGo.KeyToggle(key, down); err != nil {
			return nil, err
		}
	}

	return nil, nil
}

// typeText types text string
func (s *ComputerUseService) typeText(data json.RawMessage) (interface{}, error) {
	var params TypeTextAction
	if err := json.Unmarshal(data, &params); err != nil {
		return nil, err
	}

	return nil, s.robotGo.TypeText(params.Text, params.Delay)
}

// pasteText pastes text using clipboard
func (s *ComputerUseService) pasteText(data json.RawMessage) (interface{}, error) {
	var params PasteTextAction
	if err := json.Unmarshal(data, &params); err != nil {
		return nil, err
	}

	return nil, s.robotGo.PasteText(params.Text)
}

// wait delays execution
func (s *ComputerUseService) wait(data json.RawMessage) (interface{}, error) {
	var params WaitAction
	if err := json.Unmarshal(data, &params); err != nil {
		return nil, err
	}

	s.robotGo.Delay(params.Duration)
	return nil, nil
}

// screenshot captures screen
func (s *ComputerUseService) screenshot(data json.RawMessage) (interface{}, error) {
	log.Println("Taking screenshot")

	pngBytes, err := s.robotGo.CaptureScreenPNG()
	if err != nil {
		return nil, fmt.Errorf("failed to capture screenshot: %v", err)
	}

	base64Image := base64.StdEncoding.EncodeToString(pngBytes)

	return ScreenshotResponse{
		Image: base64Image,
	}, nil
}

// cursorPosition gets current cursor position
func (s *ComputerUseService) cursorPosition(data json.RawMessage) (interface{}, error) {
	log.Println("Getting cursor position")

	x, y, err := s.robotGo.GetCursorPosition()
	if err != nil {
		return nil, err
	}

	return CursorPositionResponse{
		X: x,
		Y: y,
	}, nil
}

// application launches or activates application
func (s *ComputerUseService) application(data json.RawMessage) (interface{}, error) {
	var params ApplicationAction
	if err := json.Unmarshal(data, &params); err != nil {
		return nil, err
	}

	log.Printf("Application action: %s", params.Application)

	// Platform-specific application commands
	var command string
	var args []string

	switch runtime.GOOS {
	case "darwin": // macOS
		command, args = s.getMacOSAppCommand(params.Application)
	case "linux":
		command, args = s.getLinuxAppCommand(params.Application)
	case "windows":
		command, args = s.getWindowsAppCommand(params.Application)
	default:
		return nil, fmt.Errorf("unsupported platform: %s", runtime.GOOS)
	}

	if command == "" {
		return nil, fmt.Errorf("unsupported application: %s", params.Application)
	}

	return nil, s.robotGo.ExecuteCommand(command, args...)
}

// getMacOSAppCommand returns command for macOS
func (s *ComputerUseService) getMacOSAppCommand(app ApplicationName) (string, []string) {
	appMap := map[ApplicationName][]string{
		AppFirefox:   {"open", "-a", "Firefox"},
		AppVSCode:    {"open", "-a", "Visual Studio Code"},
		AppTerminal:  {"open", "-a", "Terminal"},
		AppDirectory: {"open", "-a", "Finder"},
	}

	if cmd, exists := appMap[app]; exists {
		return cmd[0], cmd[1:]
	}
	return "", nil
}

// getLinuxAppCommand returns command for Linux
func (s *ComputerUseService) getLinuxAppCommand(app ApplicationName) (string, []string) {
	appMap := map[ApplicationName]string{
		AppFirefox:   "firefox",
		AppVSCode:    "code",
		AppTerminal:  "xterm",
		AppDirectory: "nautilus",
	}

	if cmd, exists := appMap[app]; exists {
		return cmd, nil
	}
	return "", nil
}

// getWindowsAppCommand returns command for Windows
func (s *ComputerUseService) getWindowsAppCommand(app ApplicationName) (string, []string) {
	appMap := map[ApplicationName]string{
		AppFirefox:   "firefox.exe",
		AppVSCode:    "code.cmd",
		AppTerminal:  "cmd.exe",
		AppDirectory: "explorer.exe",
	}

	if cmd, exists := appMap[app]; exists {
		return cmd, nil
	}
	return "", nil
}

// writeFile writes file to disk
func (s *ComputerUseService) writeFile(data json.RawMessage) (interface{}, error) {
	var params WriteFileAction
	if err := json.Unmarshal(data, &params); err != nil {
		return nil, err
	}

	log.Printf("Writing file: %s", params.Path)

	// Decode base64 data
	fileData, err := base64.StdEncoding.DecodeString(params.Data)
	if err != nil {
		return FileOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to decode base64 data: %v", err),
		}, nil
	}

	// Resolve path
	targetPath := params.Path
	if !filepath.IsAbs(targetPath) {
		homeDir, _ := os.UserHomeDir()
		targetPath = filepath.Join(homeDir, "Desktop", targetPath)
	}

	// Ensure directory exists
	dir := filepath.Dir(targetPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return FileOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to create directory: %v", err),
		}, nil
	}

	// Write file
	if err := os.WriteFile(targetPath, fileData, 0644); err != nil {
		return FileOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to write file: %v", err),
		}, nil
	}

	log.Printf("File written successfully: %s", targetPath)

	return FileOperationResponse{
		Success: true,
		Message: fmt.Sprintf("File written successfully to: %s", targetPath),
	}, nil
}

// readFile reads file from disk
func (s *ComputerUseService) readFile(data json.RawMessage) (interface{}, error) {
	var params ReadFileAction
	if err := json.Unmarshal(data, &params); err != nil {
		return nil, err
	}

	log.Printf("Reading file: %s", params.Path)

	// Resolve path
	targetPath := params.Path
	if !filepath.IsAbs(targetPath) {
		homeDir, _ := os.UserHomeDir()
		targetPath = filepath.Join(homeDir, "Desktop", targetPath)
	}

	// Read file
	fileData, err := os.ReadFile(targetPath)
	if err != nil {
		return FileOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to read file: %v", err),
		}, nil
	}

	// Get file info
	fileInfo, err := os.Stat(targetPath)
	if err != nil {
		return FileOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to get file info: %v", err),
		}, nil
	}

	// Encode to base64
	base64Data := base64.StdEncoding.EncodeToString(fileData)

	// Determine MIME type
	ext := strings.ToLower(filepath.Ext(targetPath))
	mimeType := getMimeType(ext)

	log.Printf("File read successfully: %s", targetPath)

	return FileOperationResponse{
		Success:   true,
		Data:      base64Data,
		Name:      filepath.Base(targetPath),
		Size:      fileInfo.Size(),
		MediaType: mimeType,
	}, nil
}

// getMimeType returns MIME type based on file extension
func getMimeType(ext string) string {
	mimeTypes := map[string]string{
		".pdf":  "application/pdf",
		".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
		".doc":  "application/msword",
		".txt":  "text/plain",
		".html": "text/html",
		".json": "application/json",
		".xml":  "text/xml",
		".csv":  "text/csv",
		".png":  "image/png",
		".jpg":  "image/jpeg",
		".jpeg": "image/jpeg",
		".gif":  "image/gif",
		".svg":  "image/svg+xml",
	}

	if mime, exists := mimeTypes[ext]; exists {
		return mime
	}
	return "application/octet-stream"
}
