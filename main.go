// main.go
// To run: go run .
package main

import (
	"html/template"
	"log"
	"net/http"
	"robin/nucleotide"
	"strings"
)

type PageData struct {
	Input      string
	Result     string
	Complement string
	Error      string
}

func main() {
	// Serve static files
	fs := http.FileServer(http.Dir("static"))
	http.Handle("/static/", http.StripPrefix("/static/", fs))

	// Handle main page
	http.HandleFunc("/", handleMain)

	// Handle sequence processing
	http.HandleFunc("/process", handleProcess)

	log.Println("Server starting on http://localhost:8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}

func handleMain(w http.ResponseWriter, r *http.Request) {
	tmpl := template.Must(template.ParseFiles("templates/index.html"))
	tmpl.Execute(w, PageData{})
}

func handleProcess(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Redirect(w, r, "/", http.StatusSeeOther)
		return
	}

	input := r.FormValue("sequence")
	input = strings.ToUpper(strings.TrimSpace(input))

	if input == "" {
		renderError(w, "Please enter a nucleotide sequence")
		return
	}

	// Process the sequence
	var result strings.Builder
	var complement strings.Builder

	for _, char := range input {
		nuc := nucleotide.NewNucleotide(char)
		comp := nuc.Complement()

		result.WriteString(nuc.String() + " ")
		complement.WriteString(comp.String() + " ")
	}

	data := PageData{
		Input:      input,
		Result:     result.String(),
		Complement: complement.String(),
	}

	tmpl := template.Must(template.ParseFiles("templates/index.html"))
	tmpl.Execute(w, data)
}

func renderError(w http.ResponseWriter, errMsg string) {
	data := PageData{
		Error: errMsg,
	}
	tmpl := template.Must(template.ParseFiles("templates/index.html"))
	tmpl.Execute(w, data)
}
