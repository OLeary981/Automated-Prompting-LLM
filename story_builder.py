import itertools
import user_interaction
import database
import re


def generate_stories(connection):
    user_interaction.prompt_see_all_templates(connection)
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
                fields[field] = ["default"]   # Default value if no sample data is available
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
    

