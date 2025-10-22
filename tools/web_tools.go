package jarvisTools

import (
	"context"
	"github.com/tmc/langchaingo/tools"
	"github.com/tmc/langchaingo/tools/scraper"
)

// WebScraperTool wraps the langchain scraper with a valid OpenAI function name
type WebScraperTool struct {
	scraper *scraper.Scraper
}

func NewWebScraperTool() (*WebScraperTool, error) {
	scraperTool, err := scraper.New(
		scraper.WithMaxDepth(2),        // Limit crawling depth
		scraper.WithMaxPages(5),        // Limit number of pages
		scraper.WithDelay(1000),        // 1 second delay between requests
		scraper.WithParallelsNum(2),    // Limit concurrent requests
	)
	if err != nil {
		return nil, err
	}
	
	return &WebScraperTool{scraper: scraperTool}, nil
}

func (w *WebScraperTool) Name() string {
	return "web_scraper"
}

func (w *WebScraperTool) Description() string {
	return w.scraper.Description()
}

func (w *WebScraperTool) Call(ctx context.Context, input string) (string, error) {
	return w.scraper.Call(ctx, input)
}

func GetWebTools() ([]tools.Tool, error) {
	webScraper, err := NewWebScraperTool()
	if err != nil {
		return nil, err
	}
	
	return []tools.Tool{webScraper}, nil
}