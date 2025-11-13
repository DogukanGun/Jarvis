package async

import (
	"log"
	"runtime/debug"
)

// RunAsync runs a function in the background without blocking the caller.
// It automatically recovers from panics so your app doesn't crash.
func RunAsync(fn func()) {
	go func() {
		defer func() {
			if rec := recover(); rec != nil {
				log.Printf("[async] recovered from panic: %v\n%s", rec, debug.Stack())
			}
		}()
		fn()
	}()
}
