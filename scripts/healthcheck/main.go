// Container health check for images without a shell: exits 0 when HEALTHCHECK_URL
// answers with a 2xx status, 1 otherwise.
package main

import (
	"fmt"
	"net/http"
	"os"
	"time"
)

func main() {
	url := os.Getenv("HEALTHCHECK_URL")
	if url == "" {
		fmt.Fprintln(os.Stderr, "HEALTHCHECK_URL is not set")
		os.Exit(1)
	}
	client := http.Client{Timeout: 4 * time.Second}
	response, err := client.Get(url)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	response.Body.Close()
	if response.StatusCode < 200 || response.StatusCode > 299 {
		fmt.Fprintf(os.Stderr, "%s answered %d\n", url, response.StatusCode)
		os.Exit(1)
	}
}
