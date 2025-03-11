document.addEventListener("DOMContentLoaded", function() {
    // Accordion Behavior
    document.querySelectorAll(".accordion .title").forEach(title => {
        title.addEventListener("click", function() {
            this.nextElementSibling.classList.toggle("active");
        });
    });

    // Add Domain
    document.getElementById("add-domain").addEventListener("click", function() {
        let table = document.getElementById("domains-list");
        let row = document.createElement("tr");
        row.innerHTML = `
            <td><input type="text" value="Domain ${table.children.length + 1}"></td>
            <td><input type="text"></td>
            <td><button type="button" class="delete">X</button></td>`;
        table.appendChild(row);
    });

    // Add Complex
    document.getElementById("add-complex").addEventListener("click", function() {
        let table = document.getElementById("complexes-list");
        let row = document.createElement("tr");
        row.innerHTML = `
            <td><input type="text" value="Complex ${table.children.length + 1}"></td>
            <td><input type="text"></td>
            <td><input type="text"></td>
            <td><button type="button" class="delete">X</button></td>`;
        table.appendChild(row);
    });

    // Remove Row
    document.addEventListener("click", function(event) {
        if (event.target.classList.contains("delete")) {
            event.target.parentElement.parentElement.remove();
        }
    });

    // Handle Form Submission
    document.getElementById("design-form").addEventListener("submit", async function(event) {
        event.preventDefault();
        let material = document.querySelector('input[name="material"]:checked').value;
        let temperature = document.getElementById("temperature").value;
        let trials = document.getElementById("trials").value;

        let response = await fetch("/api/design", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ material, temperature, trials })
        });

        let result = await response.json();
        document.getElementById("result-text").innerText = result.result;
        document.getElementById("output").classList.remove("hidden");
    });
});

