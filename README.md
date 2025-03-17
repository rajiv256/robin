NUPACK Design Web App

Overview

This is a web-based sequence design tool built using Go for the backend and HTML, CSS, and JavaScript (TailwindCSS) for the frontend. It allows users to configure and design RNA/DNA sequences using a structured input form.

Features

Static File Hosting – Serves CSS, JavaScript, and images from the static folder.

TailwindCSS UI – Clean and responsive UI for inputting sequence design parameters.

Go Web Server – Serves the frontend and handles HTTP requests.

Algorithm Configuration – Users can set design parameters like temperature, trials, stop conditions, and random seed.

On-Target Complexes – Configure strand orders and target structures.

Project Structure

NUPACK-Design

static/ (Static files like CSS, JS, images)

css/ (Stylesheets)

styles.css

templates/ (HTML templates)

index.html

server.go (Main Go server file)

README.md (Project documentation)

Installation and Setup

Install Go
Ensure you have Go 1.24+ installed by running:

go version

If Go is not installed, use:

brew install go

Clone the Repository

git clone https://github.com/rajiv256/robin.git
cd nupack-design

Run the Go Server

go run server.go

You should see:

Server started on http://localhost:8080

Open in Browser
Go to:

http://localhost:8080

to access the application.

Troubleshooting

If the port is already in use, you may see an error like:

listen tcp :8080: bind: address already in use

To find and kill the process using port 8080, run:

lsof -i :8080
kill -9 

If static files are not loading:

Ensure your project structure matches the one above.

Verify that the static folder exists and contains the necessary CSS files.

License

This project is licensed under the MIT License.

