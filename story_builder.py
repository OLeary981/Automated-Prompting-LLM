import itertools
import user_interaction
import database
import re


def generate_stories(connection):
    user_interaction.prompt_see_all_templates(connection)
    template_id = int(input("Enter the number of the template you are selecting: "))
    template = database.get_template_by_id(connection, template_id)
    template_filler(connection, template)
    return


def template_filler(connection, template):
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
    


# # Define the template string
# template = "There was once an {animal} who lived in {place} and always dreamed of being a {job}"

# # Define the arrays for each field
# animal_array = ["cow", "cheetah", "beetle"]
# place_array = ["Dublin", "France", "London"]
# job_array = ["professor", "popstar", "firefighter"]

# # Create a dictionary to map field names to their respective arrays
# fields = {
#     "animal": animal_array,
#     "place": place_array,
#     "job": job_array
# }

# # Extract the field names from the template
# field_names = [field.strip("{}") for field in template.split() if field.startswith("{") and field.endswith("}")]

# # Generate all possible permutations
# permutations = list(itertools.product(*(fields[field] for field in field_names)))

# # Print the number of stories that will be generated
# print(f"Number of stories that will be generated: {len(permutations)}")

# # Replace the placeholders in the template with the permutations
# for permutation in permutations:
#     story = template
#     for field, value in zip(field_names, permutation):
#         story = story.replace(f"{{{field}}}", value)
#     print(story)