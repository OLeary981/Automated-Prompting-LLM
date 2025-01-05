import itertools
import data_access
import database
import re


def generate_stories(connection):
    data_access.prompt_see_all_templates(connection)
    template_id = int(input("Enter the number of the template you are selecting: "))
    template = database.get_template_by_id(connection, template_id)
    template_filler(connection, template, template_id)
    return


def template_filler(connection, template, template_id):
     # Extract the field names from the template
    field_names = re.findall(r'\{(.*?)\}', template)
    print(field_names)

    # Create a dictionary to map field names to their respective arrays
    fields = {}
    for field in field_names:
            words = database.get_words_by_field(connection, field)
            if words:
                fields[field] = words
            else:
                user_input = input(f"No sample data available for field '{field}'. Please enter values separated by commas: ")
                fields[field] = [value.strip() for value in user_input.split(',')] if user_input else ["default"]  # Use user input or default if input is empty
            print(f"Field: {field}, Words: {fields[field]}")

    # Generate all possible permutations
    permutations = list(itertools.product(*(fields[field] for field in field_names)))

    # Print the number of stories that will be generated
    print(f"Number of stories that will be generated: {len(permutations)}")

    # Replace the placeholders in the template with the permutations
    for permutation in permutations:
        story = template
        for field, value in zip(field_names, permutation):
            story = story.replace(f"{{{field}}}", value)
        print(story)
        database.add_story(connection, story, template_id)
    

