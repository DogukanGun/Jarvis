package main

// AnalyzeScreenRequest represents a request to analyze a screenshot
type AnalyzeScreenRequest struct {
	Action      string `json:"action"`      // "find_element", "detect_text", "describe_screen", "find_coordinates"
	Screenshot  string `json:"screenshot"`  // Base64 encoded image
	Query       string `json:"query"`       // What to find (e.g., "submit button", "login field")
	Description string `json:"description"` // Additional context
}

// AnalyzeScreenResponse represents the response from screen analysis
type AnalyzeScreenResponse struct {
	Success     bool              `json:"success"`
	Action      string            `json:"action"`
	Elements    []DetectedElement `json:"elements,omitempty"`
	Description string            `json:"description,omitempty"`
	Error       string            `json:"error,omitempty"`
}

// DetectedElement represents a UI element found on screen
type DetectedElement struct {
	Name        string       `json:"name"`        // Element name/type (e.g., "Submit Button")
	Coordinates Coordinates  `json:"coordinates"` // Center coordinates
	BoundingBox *BoundingBox `json:"boundingBox,omitempty"`
	Confidence  float64      `json:"confidence"` // 0.0 - 1.0
	Description string       `json:"description,omitempty"`
	Text        string       `json:"text,omitempty"` // OCR text if available
}

// Coordinates represents x,y position on screen
type Coordinates struct {
	X int `json:"x"`
	Y int `json:"y"`
}

// BoundingBox represents element boundaries
type BoundingBox struct {
	X      int `json:"x"`      // Top-left x
	Y      int `json:"y"`      // Top-left y
	Width  int `json:"width"`  // Box width
	Height int `json:"height"` // Box height
}

// ScreenDescription represents full screen analysis
type ScreenDescription struct {
	Summary      string            `json:"summary"`
	Elements     []DetectedElement `json:"elements"`
	TextContent  []string          `json:"textContent,omitempty"`
	Applications []string          `json:"applications,omitempty"` // Detected apps
	Layout       string            `json:"layout,omitempty"`
}

// VisionModelRequest represents request to vision model
type VisionModelRequest struct {
	Model    string    `json:"model"`
	Messages []Message `json:"messages"`
	Stream   bool      `json:"stream"`
}

// Message represents a chat message with optional images
type Message struct {
	Role    string   `json:"role"`
	Content string   `json:"content,omitempty"`
	Images  []string `json:"images,omitempty"` // Base64 encoded images
}

// VisionModelResponse represents response from vision model
type VisionModelResponse struct {
	Model     string  `json:"model"`
	CreatedAt string  `json:"created_at"`
	Message   Message `json:"message"`
	Done      bool    `json:"done"`
}

// HealthResponse for health check
type HealthResponse struct {
	Status string `json:"status"`
	Agent  string `json:"agent"`
	Model  string `json:"model"`
}
