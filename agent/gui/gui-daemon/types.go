package main

import "encoding/json"

// Coordinates represents x,y coordinates on screen
type Coordinates struct {
	X int `json:"x"`
	Y int `json:"y"`
}

// ButtonType represents mouse button types
type ButtonType string

const (
	ButtonLeft   ButtonType = "left"
	ButtonRight  ButtonType = "right"
	ButtonMiddle ButtonType = "middle"
)

// PressType represents key/button press state
type PressType string

const (
	PressDown PressType = "down"
	PressUp   PressType = "up"
)

// ScrollDirection represents scroll direction
type ScrollDirection string

const (
	ScrollUp    ScrollDirection = "up"
	ScrollDown  ScrollDirection = "down"
	ScrollLeft  ScrollDirection = "left"
	ScrollRight ScrollDirection = "right"
)

// ApplicationName represents supported applications
type ApplicationName string

const (
	AppFirefox     ApplicationName = "firefox"
	AppThunderbird ApplicationName = "thunderbird"
	AppVSCode      ApplicationName = "vscode"
	AppTerminal    ApplicationName = "terminal"
	AppDirectory   ApplicationName = "directory"
	AppDesktop     ApplicationName = "desktop"
)

// ComputerAction represents the base action structure
type ComputerAction struct {
	Action string          `json:"action"`
	Data   json.RawMessage `json:"-"`
}

// UnmarshalJSON custom unmarshaler to preserve raw data
func (c *ComputerAction) UnmarshalJSON(data []byte) error {
	type Alias ComputerAction
	aux := &struct {
		*Alias
	}{
		Alias: (*Alias)(c),
	}
	if err := json.Unmarshal(data, &aux); err != nil {
		return err
	}
	c.Data = data
	return nil
}

// MoveMouseAction moves cursor to coordinates
type MoveMouseAction struct {
	Action      string      `json:"action"`
	Coordinates Coordinates `json:"coordinates"`
}

// TraceMouseAction moves mouse along a path
type TraceMouseAction struct {
	Action   string        `json:"action"`
	Path     []Coordinates `json:"path"`
	HoldKeys []string      `json:"holdKeys,omitempty"`
}

// ClickMouseAction performs mouse click
type ClickMouseAction struct {
	Action      string       `json:"action"`
	Coordinates *Coordinates `json:"coordinates,omitempty"`
	Button      ButtonType   `json:"button"`
	HoldKeys    []string     `json:"holdKeys,omitempty"`
	ClickCount  int          `json:"clickCount"`
}

// PressMouseAction presses or releases mouse button
type PressMouseAction struct {
	Action      string       `json:"action"`
	Coordinates *Coordinates `json:"coordinates,omitempty"`
	Button      ButtonType   `json:"button"`
	Press       PressType    `json:"press"`
}

// DragMouseAction drags mouse along a path
type DragMouseAction struct {
	Action   string        `json:"action"`
	Path     []Coordinates `json:"path"`
	Button   ButtonType    `json:"button"`
	HoldKeys []string      `json:"holdKeys,omitempty"`
}

// ScrollAction performs scroll operation
type ScrollAction struct {
	Action      string          `json:"action"`
	Coordinates *Coordinates    `json:"coordinates,omitempty"`
	Direction   ScrollDirection `json:"direction"`
	ScrollCount int             `json:"scrollCount"`
	HoldKeys    []string        `json:"holdKeys,omitempty"`
}

// TypeKeysAction types key combination
type TypeKeysAction struct {
	Action string   `json:"action"`
	Keys   []string `json:"keys"`
	Delay  int      `json:"delay,omitempty"`
}

// PressKeysAction holds or releases keys
type PressKeysAction struct {
	Action string    `json:"action"`
	Keys   []string  `json:"keys"`
	Press  PressType `json:"press"`
}

// TypeTextAction types text string
type TypeTextAction struct {
	Action string `json:"action"`
	Text   string `json:"text"`
	Delay  int    `json:"delay,omitempty"`
}

// PasteTextAction pastes text using clipboard
type PasteTextAction struct {
	Action string `json:"action"`
	Text   string `json:"text"`
}

// WaitAction delays execution
type WaitAction struct {
	Action   string `json:"action"`
	Duration int    `json:"duration"` // milliseconds
}

// ScreenshotAction captures screen
type ScreenshotAction struct {
	Action string `json:"action"`
}

// CursorPositionAction gets cursor position
type CursorPositionAction struct {
	Action string `json:"action"`
}

// ApplicationAction launches/activates application
type ApplicationAction struct {
	Action      string          `json:"action"`
	Application ApplicationName `json:"application"`
}

// WriteFileAction writes file to disk
type WriteFileAction struct {
	Action string `json:"action"`
	Path   string `json:"path"`
	Data   string `json:"data"` // Base64 encoded
}

// ReadFileAction reads file from disk
type ReadFileAction struct {
	Action string `json:"action"`
	Path   string `json:"path"`
}

// Response represents API response
type Response struct {
	Success bool        `json:"success"`
	Data    interface{} `json:"data,omitempty"`
	Error   string      `json:"error,omitempty"`
}

// ScreenshotResponse for screenshot action
type ScreenshotResponse struct {
	Image string `json:"image"` // Base64 encoded PNG
}

// CursorPositionResponse for cursor position action
type CursorPositionResponse struct {
	X int `json:"x"`
	Y int `json:"y"`
}

// FileOperationResponse for file read/write operations
type FileOperationResponse struct {
	Success   bool   `json:"success"`
	Message   string `json:"message,omitempty"`
	Data      string `json:"data,omitempty"`      // Base64 for read
	Name      string `json:"name,omitempty"`      // Filename
	Size      int64  `json:"size,omitempty"`      // File size
	MediaType string `json:"mediaType,omitempty"` // MIME type
}
