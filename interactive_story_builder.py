import itertools
import re
import database

def prompt_user_for_template():
    template = input("Enter the template, using {field} notation for blank types: ")
    return template

def prompt_user_for_words(field_names):
    fields = {}
    for field in field_names:
        words = input(f"Enter words for {field} (comma-separated): ").split(',')
        fields[field] = [word.strip() for word in words]
    return fields

def store_template_and_words(connection, template, fields):
    # Store the template in the database
    template_id = database.add_template(connection, template)

    # Store the words and fields in the database
    for field, words in fields.items():
        for word in words:
            database.add_word_with_field(connection, word, field)

    return template_id

def generate_stories_manual(connection):
    template = prompt_user_for_template()
    field_names = re.findall(r'\{(.*?)\}', template)
    fields = prompt_user_for_words(field_names)
    template_id = store_template_and_words(connection, template, fields)

    # Generate all possible permutations
    permutations = list(itertools.product(*(fields[field] for field in field_names)))

    # Print the number of stories that will be generated
    print(f"Number of stories that will be generated: {len(permutations)}")

    # Replace the placeholders in the template with the permutations and add each story to the database
    for permutation in permutations:
        story = template
        for field, value in zip(field_names, permutation):
            story = story.replace(f"{{{field}}}", value)
        print(story)
        database.add_story(connection, story, template_id)

# Example usage
if __name__ == "__main__":
    connection = database.connect()
    generate_stories_manual(connection)