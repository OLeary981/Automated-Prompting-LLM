const fieldData = {};
const allWords = {};

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

/**
 * Ensures that each field in fieldData contains only unique words
 * @returns {boolean} True if changes were made, false otherwise
 */
function ensureUniqueWordsInFields() {
    let changesMade = false;

    // Iterate through each field
    for (const fieldName in fieldData) {
        // Get current words in this field
        const words = fieldData[fieldName];

        // Skip if no words or only one word (can't have duplicates)
        if (!words || words.length <= 1) continue;

        // Create a Set to get unique words (preserving original order)
        const uniqueWords = [];
        const seen = new Set();

        words.forEach(word => {
            if (!seen.has(word)) {
                seen.add(word);
                uniqueWords.push(word);
            } else {
                changesMade = true;
                console.warn(`Duplicate word "${word}" found in field "${fieldName}" - removing duplicate`);
            }
        });

        // Update fieldData if changes were made
        if (uniqueWords.length !== words.length) {
            fieldData[fieldName] = uniqueWords;
        }
    }

    return changesMade;
}

function refreshUI() {
    console.log("Refreshing UI...");

    // Ensure no duplicate words
    const uniqueChanges = ensureUniqueWordsInFields();
    if (uniqueChanges) {
        console.log("Removed duplicate words from fields");
    }

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

/**
 * Associates a word with a field
 * @param {string} word - The word to associate
 * @param {string} field - The field to associate with
 */
function associateWordWithField(word, field) {
    if (!allWords[word]) {
        allWords[word] = [];
    }
    if (!allWords[word].includes(field)) {
        allWords[word].push(field);
    }
}

/**
 * Removes an association between a word and field
 * @param {string} word - The word to update
 * @param {string} field - The field to remove
 */
function removeFieldAssociation(word, field) {
    if (allWords[word]) {
        allWords[word] = allWords[word].filter(f => f !== field);
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

    if (fieldName) {
        associateWordWithField(word, fieldName);
    }

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
    delete allWords[word]; 

    if (fieldData[fieldName]) {
        fieldData[fieldName] = fieldData[fieldName].filter(w => w !== word);
    }

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

    // Group unused words by their originating fields
    Object.keys(allWords).forEach(word => {
        if (!usedWords.has(word)) {
            // Use the first field the word is associated with
            const fields = allWords[word];
            if (fields && fields.length > 0) {
                const primaryField = fields[0]; // Use first field as primary
                if (!fieldGroups[primaryField]) {
                    fieldGroups[primaryField] = [];
                }
                fieldGroups[primaryField].push(word);
            }
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
    // Make both field containers and word containers droppable
    const allDropTargets = document.querySelectorAll('.field-words, .word-container');

    allDropTargets.forEach(container => {
        container.addEventListener('dragover', e => e.preventDefault());
        container.addEventListener('drop', e => {
            e.preventDefault();
            const word = e.dataTransfer.getData('text/plain');
            const fromEl = document.querySelector('.dragging');
            if (!fromEl) return;

            // Determine source and target fields
            const fromFieldContainer = fromEl.closest('.field-words');
            const fromWordContainer = fromEl.closest('.word-container');
            const isFromField = fromFieldContainer !== null;
            const isToField = container.classList.contains('field-words');

            const fromField = isFromField ? fromFieldContainer.dataset.field :
                (fromWordContainer ? fromWordContainer.dataset.field : null);
            const toField = container.dataset.field;

            console.log(`Dragging "${word}" from ${isFromField ? 'field' : 'available'} (${fromField}) to ${isToField ? 'field' : 'available'} (${toField})`);

            // Don't do anything if dragging to the same container type and field
            if (fromField === toField && isFromField === isToField) return;

            // Remove from source field if coming from a field
            if (isFromField && fieldData[fromField]) {
                fieldData[fromField] = fieldData[fromField].filter(w => w !== word);
            }

            // Add to target field if going to a field
            if (isToField) {
                if (!fieldData[toField]) fieldData[toField] = [];
                if (!fieldData[toField].includes(word)) {
                    fieldData[toField].push(word);
                    associateWordWithField(word, toField);
                }

                // Only persist to database when adding to a field
                addWordsToField(toField, word);
            }

            // Remove UI element and refresh
            fromEl.remove();
            ensureUniqueWordsInFields();
            refreshUI();
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
            ensureUniqueWordsInFields();

            const container = document.getElementById(`field-${field}`);
            words.forEach(word => {
                if (!fieldData[field]) fieldData[field] = [];
                if (!fieldData[field].includes(word)) {
                    fieldData[field].push(word);
                    associateWordWithField(word, field);


                }
            });
            addWordsToField(field, words);

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

/**
 * Adds one or more words to a field
 * @param {string} fieldName - The field to add words to
 * @param {string|string[]} words - Single word or array of words to add
 */
function addWordsToField(fieldName, words) {
    // Convert array of words to comma-separated string if needed
    const wordsString = Array.isArray(words) ? words.join(',') : words;

    fetch('/add_word', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            field_name: fieldName,
            new_words: wordsString,
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
                console.log(`Words added to field "${fieldName}": ${wordsString}`);
            } else {
                console.error(`Failed to add words: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });

}

function initialize() {
    document.querySelectorAll('.field-words').forEach(fieldDiv => {
        const field = fieldDiv.dataset.field;
        fieldData[field] = [];
        fieldDiv.querySelectorAll('.word-badge').forEach(el => {
            const word = el.dataset.word;
            fieldData[field].push(word);
            associateWordWithField(word, field);
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
    ensureUniqueWordsInFields();
    refreshUI();
}

$('#wordActionModal').on('hide.bs.modal', function () {
    // fix for accessibility problem (Aria-hidden thing)
    document.activeElement.blur();
});

document.addEventListener('DOMContentLoaded', initialize);