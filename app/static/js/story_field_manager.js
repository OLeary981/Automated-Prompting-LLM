const fieldData = {};
const allWords = new Map(); // word -> original field

function updateField(fieldName, action, word) {
    if (!fieldData[fieldName]) fieldData[fieldName] = [];

    if (action === 'add' && !fieldData[fieldName].includes(word)) {
        fieldData[fieldName].push(word);
    } else if (action === 'remove') {
        fieldData[fieldName] = fieldData[fieldName].filter(w => w !== word);
    }

    refreshUI();
    calculatePermutations(); // Ensure permutations are recalculated immediately
}

function refreshUI() {
    console.log("Refreshing UI...");
    
    // Update each field container
    for (const [fieldName, words] of Object.entries(fieldData)) {
        const fieldContainer = document.getElementById(`field-${fieldName}`);
        if (fieldContainer) {
            // Clear existing word badges
            fieldContainer.innerHTML = '';
            
            // Add word badges for each word
            words.forEach(word => {
                const badge = createWordBadge(word, fieldName);
                fieldContainer.appendChild(badge);
            });
        }
    }
    updateAvailableWords();
    updateFieldDataJson();
    calculatePermutations();
    setupDragDrop();
}

function updateFieldDataJson() {
    const fieldDataInput = document.getElementById('field-data-json');
    if (fieldDataInput) {
        fieldDataInput.value = JSON.stringify(fieldData);
        calculatePermutations();
    } else {
        console.error("Field data JSON input not found!");
    }
}

function calculatePermutations() {
    const countEl = document.getElementById('permutation-count');
    const warningEl = document.getElementById('permutation-warning');
    const emptyWarning = document.getElementById('empty-fields-warning');

    // Return early if essential elements don't exist
    if (!countEl) {
        console.warn("Permutation count element not found");
        return;
    }

    const empty = Object.values(fieldData).some(words => words.length === 0);
    
    if (empty) {
        countEl.textContent = '0';
        
        if (emptyWarning) {
            emptyWarning.style.display = 'block';
        }
        
        if (warningEl) {
            warningEl.style.display = 'none';
        }
        return;
    } else {
        if (emptyWarning) {
            emptyWarning.style.display = 'none';
        }
    }

    let total = 1;
    Object.values(fieldData).forEach(words => total *= words.length);
    countEl.textContent = total.toLocaleString();
    
    if (warningEl) {
        warningEl.style.display = total > 100 ? 'block' : 'none';
    }
}

function createWordBadge(word, fieldName) {
    const badge = document.createElement('div');
    badge.className = 'word-badge';
    badge.draggable = true;
    badge.dataset.word = word;
    badge.innerHTML = `${word} <span class="word-remove">&times;</span>`;

    badge.addEventListener('dragstart', handleDragStart);
    badge.addEventListener('dragend', handleDragEnd);
    badge.addEventListener('click', () => handleWordClick(word, fieldName));
    badge.querySelector('.word-remove').addEventListener('click', e => {
        e.stopPropagation();
        handleWordClick(word, fieldName);
    });

    if (fieldName) allWords.set(word, fieldName);
    return badge;
}

function handleWordClick(word, fieldName) {
    // Show the confirmation modal
    $('#wordActionModal').modal('show');

    // Handle "Delete from Database" action
    document.getElementById('deleteWordBtn').onclick = () => {
        deleteWordFromDatabase(fieldName, word);
        $('#wordActionModal').modal('hide'); // Hide the modal after the action
        refreshUI();
    };

    // Handle "Remove from Group" action
    document.getElementById('removeWordBtn').onclick = () => {
        updateField(fieldName, 'remove', word);
        refreshUI();
        $('#wordActionModal').modal('hide'); // Hide the modal after the action
    };
}

function deleteWordFromDatabase(fieldName, word) {
    // Immediately remove from allWords so it doesn't show in Available Words
    // even if the API call takes time
    allWords.delete(word);
    
    // Remove from fieldData
    updateField(fieldName, 'remove', word);
    
    // Then perform the API call
    fetch('/delete_word', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            field_name: fieldName,
            word: word,
        }),
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                console.error(`Error: ${data.message || 'Unknown error'}`);
                throw new Error(data.message || 'Failed to delete word');
            });
        }
        return response.json();
    })
    .then(data => {
        console.log(`Server response: ${JSON.stringify(data)}`);
        
        if (data.success) {
            console.log(`Word "${word}" deleted from the database.`);
            // The operation succeeded, make sure allWords doesn't have this word
            allWords.delete(word);
            refreshUI();
        } else {
            console.error(`Failed to delete word: ${data.message}`);
            // Maybe show an error message to the user
        }
    })
}

function handleDragStart(e) {
    e.dataTransfer.setData('text/plain', e.target.dataset.word);
    e.target.classList.add('dragging');
}

function handleDragEnd(e) {
    e.target.classList.remove('dragging');
}

function updateAvailableWords() {
    const container = document.getElementById('available-words-container');
    container.innerHTML = '';

    const usedWords = new Set(Object.values(fieldData).flat());
    const fieldGroups = {};

    allWords.forEach((field, word) => {
        if (!usedWords.has(word)) {
            if (!fieldGroups[field]) fieldGroups[field] = [];
            fieldGroups[field].push(word);
        }
    });

    for (const [field, words] of Object.entries(fieldGroups)) {
        const title = document.createElement('h6');
        title.className = 'mt-3 mb-2 border-bottom pb-1';
        title.textContent = field;
        container.appendChild(title);

        const box = document.createElement('div');
        box.className = 'word-container';
        box.dataset.field = field;

        words.forEach(word => box.appendChild(createWordBadge(word, field)));
        container.appendChild(box);
    }

    if (!Object.keys(fieldGroups).length) {
        const msg = document.createElement('p');
        msg.className = 'text-muted text-center py-3';
        msg.textContent = 'All words are currently assigned to fields.';
        container.appendChild(msg);
    }

    setupDragDrop();
}

function setupDragDrop() {
    document.querySelectorAll('.word-container').forEach(container => {
        container.addEventListener('dragover', e => e.preventDefault());
        container.addEventListener('drop', e => {
            e.preventDefault();
            const word = e.dataTransfer.getData('text/plain');
            const fromEl = document.querySelector('.dragging');
            if (!fromEl) return;

            const fromContainer = fromEl.closest('.word-container');
            const fromField = fromContainer?.dataset.field;
            const toField = container.dataset.field;

            if (fromField && fromField !== toField) {
                updateField(fromField, 'remove', word);
            }

            if (toField) {
                updateField(toField, 'add', word);
                const newBadge = createWordBadge(word, toField);
                container.appendChild(newBadge);

                // Persist the word to the database
                handleWordAddition(toField, word);
            }

            fromEl.remove();
        });
    });
}

function initAddButtons() {
    document.querySelectorAll('.add-words-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const field = btn.dataset.field;
            const input = document.querySelector(`.new-words[data-field="${field}"]`);
            if (!input) {
                console.error(`Input field for field "${field}" not found.`);
                return;
            }

            const words = input.value.split(',').map(w => w.trim()).filter(Boolean);
            if (words.length === 0) {
                console.warn(`No valid words entered for field "${field}".`);
                return;
            }

            const container = document.getElementById(`field-${field}`);
            words.forEach(word => {
                if (!fieldData[field]) fieldData[field] = [];
                if (!fieldData[field].includes(word)) {
                    fieldData[field].push(word);
                    allWords.set(word, field);
                    const badge = createWordBadge(word, field);
                    container.appendChild(badge);

                    // Persist the word to the database
                    handleWordAddition(field, word);
                }
            });

            input.value = ''; // Clear the input field
            refreshUI();
        });
    });
}

function initClearButtons() {
    document.querySelectorAll('.clear-field-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const field = btn.dataset.field;
            fieldData[field] = [];
            document.getElementById(`field-${field}`).innerHTML = '';
            refreshUI();
        });
    });
}

function addWordToField(fieldName, word) {
    fetch('/add_word', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            field_name: fieldName,
            new_words: word,
        }),
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            console.log(`Word "${word}" added to field "${fieldName}"`);
        } else {
            console.error(`Failed to add word: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
    refreshUI();
}

function handleWordAddition(fieldName, word) {
    addWordToField(fieldName, word);
}

function initialize() {
    document.querySelectorAll('.field-words').forEach(fieldDiv => {
        const field = fieldDiv.dataset.field;
        fieldData[field] = [];
        fieldDiv.querySelectorAll('.word-badge').forEach(el => {
            const word = el.dataset.word;
            fieldData[field].push(word);
            allWords.set(word, field);
            el.addEventListener('click', () => handleWordClick(word, field));
            el.querySelector('.word-remove').addEventListener('click', e => {
                e.stopPropagation();
                handleWordClick(word, field);
            });
            el.addEventListener('dragstart', handleDragStart);
            el.addEventListener('dragend', handleDragEnd);
        });
    });

    initAddButtons();
    initClearButtons();
    setupDragDrop();
    refreshUI();
}

document.addEventListener('DOMContentLoaded', initialize);