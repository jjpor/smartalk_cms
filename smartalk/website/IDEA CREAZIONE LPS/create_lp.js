document.addEventListener('DOMContentLoaded', () => {
    const sectionsContainer = document.getElementById('sections-container');
    const addSectionBtn = document.getElementById('add-section-btn');
    const sectionTemplate = document.getElementById('section-template');
    const lessonForm = document.getElementById('lesson-form');

    let sectionCounter = 0; // To ensure unique IDs if needed later

    // Function to add a new section card
    function addSection() {
        sectionCounter++;
        const newSection = sectionTemplate.cloneNode(true);
        newSection.id = `section-${sectionCounter}`; // Give the card a unique ID
        newSection.style.display = 'block'; // Make it visible

        // Update title maybe?
        const titleElement = newSection.querySelector('h3');
        if (titleElement) {
            titleElement.textContent = `Section ${sectionCounter}`;
        }

        // Add event listener for the remove button
        const removeBtn = newSection.querySelector('.remove-section-btn');
        if (removeBtn) {
            removeBtn.addEventListener('click', () => {
                newSection.remove();
                // Optional: Renumber sections if needed
            });
        }

        sectionsContainer.appendChild(newSection);
    }

    // Add initial section on page load
    addSection();

    // Event listener for the "Add Section" button
    addSectionBtn.addEventListener('click', addSection);

    // Event listener for form submission
    lessonForm.addEventListener('submit', async (event) => {
        event.preventDefault(); // Prevent default browser submission

        const lessonData = {
            title: document.getElementById('lesson-title').value.trim(),
            subtitle: document.getElementById('lesson-subtitle').value.trim(),
            sections: []
        };

        // Gather data from each section card
        const sectionCards = sectionsContainer.querySelectorAll('.section-card');
        let isValid = true;
        sectionCards.forEach(card => {
            const sectionIdInput = card.querySelector('input[name="section_id"]');
            const sectionTitleInput = card.querySelector('input[name="section_title"]');
            const sectionContentTextarea = card.querySelector('textarea[name="section_content"]');

            // Basic validation check
            if (!sectionIdInput || !sectionTitleInput || !sectionContentTextarea ||
                !sectionIdInput.value.trim() || !sectionTitleInput.value.trim() || !sectionContentTextarea.value.trim()) {
                isValid = false;
                // Add some visual feedback for missing fields if desired
                card.style.borderColor = 'red';
            } else {
                 card.style.borderColor = '#e5e7eb'; // Reset border color
                 lessonData.sections.push({
                    id: sectionIdInput.value.trim(),
                    title: sectionTitleInput.value.trim(),
                    content: sectionContentTextarea.value // Keep raw HTML content
                 });
            }
        });

        if (!isValid) {
            alert('Please fill in all fields for each section.');
            return;
        }

        if (lessonData.sections.length === 0) {
            alert('Please add at least one section.');
            return;
        }

        // Send data to the backend API endpoint
        try {
            const response = await fetch('/admin/create-lesson', { // Your FastAPI endpoint URL
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    // Add authentication headers if needed (e.g., JWT)
                    // 'Authorization': `Bearer ${your_token}`
                },
                body: JSON.stringify(lessonData)
            });

            if (response.ok) {
                const result = await response.json(); // Assuming backend returns JSON
                alert('Lesson Plan created successfully!');
                // Optionally redirect or clear the form
                // window.location.href = `/auth/lesson-plans/${result.slug}`; // If backend returns the slug
                lessonForm.reset();
                sectionsContainer.innerHTML = ''; // Clear sections
                addSection(); // Add one empty section back
            } else {
                const errorData = await response.json();
                alert(`Error creating lesson plan: ${errorData.detail || response.statusText}`);
            }
        } catch (error) {
            console.error('Error submitting form:', error);
            alert('An error occurred while submitting the form. Please check the console.');
        }
    });
});