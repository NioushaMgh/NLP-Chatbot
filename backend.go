package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os/exec"
	"strings"
	"time"

	"github.com/google/uuid"
	_ "github.com/lib/pq"
)

// Database connection
var db *sql.DB

// Initialize the database
func initDB() {
	var err error
	connStr := "postgres://myuser:1234@localhost/mydatabase?sslmode=disable"
	db, err = sql.Open("postgres", connStr) // Fixed shadowing of the global `db`
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}

	// Test database connection
	if err = db.Ping(); err != nil {
		log.Fatalf("Failed to ping database: %v", err)
	}

	// Create jobs table if it doesn't exist
	_, err = db.Exec(`
		CREATE TABLE IF NOT EXISTS jobs (
			id UUID PRIMARY KEY,
			question TEXT NOT NULL,
			status TEXT NOT NULL,
			result TEXT,
			created_at TIMESTAMP DEFAULT NOW()
		)
	`)
	if err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
}

// Job structure
type Job struct {
	ID       string `json:"id"`
	Question string `json:"question"`
	Status   string `json:"status"`
	Result   string `json:"result,omitempty"`
}

// Middleware to enable CORS
func enableCORS(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*") // Set to a specific origin for production
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}

// /query endpoint: Enqueue the job
func queryHandler(w http.ResponseWriter, r *http.Request) {
	log.Println("Received a request at /query")

	var req struct {
		Question string `json:"question"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request payload", http.StatusBadRequest)
		log.Printf("Error parsing request: %v\n", err)
		return
	}

	jobID := uuid.New().String()
	_, err := db.Exec("INSERT INTO jobs (id, question, status) VALUES ($1, $2, $3)", jobID, req.Question, "in progress")
	if err != nil {
		http.Error(w, "Failed to enqueue job", http.StatusInternalServerError)
		log.Printf("Error inserting job into database: %v\n", err)
		return
	}

	go processJob(jobID, req.Question)

	json.NewEncoder(w).Encode(map[string]string{"job_id": jobID})
}
func toJSON(data interface{}) string {
	bytes, _ := json.Marshal(data)
	return string(bytes)
}

// /status endpoint: Check job status and stream updates
func statusHandler(w http.ResponseWriter, r *http.Request) {
	log.Println("Received a request for SSE at /status")

	jobID := r.URL.Query().Get("job_id")
	if jobID == "" {
		http.Error(w, "Job ID is required", http.StatusBadRequest)
		return
	}

	// Set headers for SSE
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")

	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "Streaming not supported", http.StatusInternalServerError)
		return
	}

	ticker := time.NewTicker(3 * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		var status string
		var result sql.NullString // Handle potential NULL results
		err := db.QueryRow("SELECT status, result FROM jobs WHERE id = $1", jobID).Scan(&status, &result)
		if err != nil {
			if err == sql.ErrNoRows {
				fmt.Fprintf(w, "event: error\ndata: Job not found\n\n")
				flusher.Flush()
				return
			}
			fmt.Fprintf(w, "event: error\ndata: Database error\n\n")
			flusher.Flush()
			return
		}

		// Send updates based on job status
		if status == "in progress" {
			fmt.Fprintf(w, "event: processing\ndata: Job is still being processed\n\n")
			flusher.Flush()
			continue
		}

		if status == "completed" {
			if result.Valid {
				fmt.Fprintf(w, "event: completed\ndata: %s\n\n", toJSON(map[string]string{
					"status": "completed",
					"result": result.String,
				}))
			} else {
				fmt.Fprintf(w, "event: completed\ndata: %s\n\n", toJSON(map[string]string{
					"status": "completed",
					"result": "No result available",
				}))
			}
			flusher.Flush()
			return
		}

	}
}

// Background job processing
func processJob(jobID, question string) {
	log.Printf("Processing job: %s\n", jobID)

	cmd := exec.Command("/usr/local/bin/python3", "nlp.py")
	cmd.Stdin = strings.NewReader(question)
	output, err := cmd.Output()
	if err != nil {
		log.Printf("Error executing Python script: %v\n", err)
		updateJobStatus(jobID, "failed", fmt.Sprintf("Error: %v", err))
		return
	}

	result := strings.TrimSpace(string(output))
	updateJobStatus(jobID, "completed", result)
	log.Printf("Job %s completed successfully\n", jobID)
}

// Update job status in the database
func updateJobStatus(jobID, status, result string) {
	_, err := db.Exec("UPDATE jobs SET status = $1, result = $2 WHERE id = $3", status, result, jobID)
	if err != nil {
		log.Printf("Error updating job %s: %v\n", jobID, err)
	} else {
		log.Printf("Job %s updated to status: %s\n", jobID, status)
	}
}

func main() {
	initDB()
	defer db.Close() // Ensure the database is properly closed

	mux := http.NewServeMux()
	mux.HandleFunc("/query", queryHandler)
	mux.HandleFunc("/status", statusHandler)

	handler := enableCORS(mux)

	log.Println("Server is running on http://localhost:8080")
	log.Fatal(http.ListenAndServe(":8080", handler))
}
