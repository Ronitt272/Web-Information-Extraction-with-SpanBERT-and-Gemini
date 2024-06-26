import sys, os, requests, spacy
import google.generativeai as genai

from googleapiclient.discovery import build
from bs4 import BeautifulSoup
from spacy_help_functions import create_entity_pairs
from spanbert import SpanBERT
from collections import defaultdict

# X is set of extracted tuples
X = defaultdict(int)
seen_urls = set()


spacy2bert = { 
        "ORG": "ORGANIZATION",
        "PERSON": "PERSON",
        "GPE": "LOCATION", 
        "LOC": "LOCATION",
        "DATE": "DATE"
        }

bert2spacy = {
        "ORGANIZATION": "ORG",
        "PERSON": "PERSON",
        "LOCATION": "LOC",
        "CITY": "GPE",
        "COUNTRY": "GPE",
        "STATE_OR_PROVINCE": "GPE",
        "DATE": "DATE"
        }

def get_query():
    api_key = os.environ.get('API_KEY', None)
    engine_id = os.environ.get('ENGINE_ID', None)
    gemini_key = os.environ.get('GEMINI_API_KEY', None)

    if len(sys.argv) == 9:
        model, api_key, engine_id, gemini_key, r, t, q, k = sys.argv[1:9]
    elif len(sys.argv) == 6:
        model, r, t, q, k = sys.argv[1:6]
    else:
        print("Error: Please provide either command line arguments in the format '[-spanbert|gemini] <google api key> <google engine id> <google gemini api key> <r> <t> <q> <k>', or set the required environment variables and provide arguments in the format '[-spanbert|-gemini] <r> <t> <q> <k>'.")
        sys.exit(1)
    
    return [model[1:], api_key, engine_id, gemini_key, int(r), float(t), q, int(k)]

def search(api_key, engine_id, query):
    service = build("customsearch", "v1", developerKey=api_key)
    res = (
        service.cse()
        .list(
            q=query, 
            cx=engine_id,
        )
        .execute()
    )
    return res

def print_param(user_input, iter):
    model, api_key, engine_id, gemini_key, r, t, q, k = user_input
    print("Parameters:")
    print(f"Client key   = {api_key}")
    print(f"Engine key   = {engine_id}")
    print(f"Gemini key   = {gemini_key}")
    print(f"Method       = {model}")
    print(f"Relation     = {r}")
    print(f"Threshold    = {t}")
    print(f"Query        = {q}")
    print(f"# of Tuples  = {k}")
    print("Loading necessary libraries; This should take a minute or so ...)")
    print(f"=========== Iteration: {iter} - Query: {q} ===========")


def run_spanbert(entity_pairs, t, spanbert, r):
    preds = spanbert.predict(entity_pairs)
    extracted = 0
    extraction_added = 0
    for ex, pred in list(zip(entity_pairs, preds)):
        relation = pred[0]
        # Check if the predicted relation match user input r
        if (r == 1 and relation != 'per:schools_attended') or (r == 2 and relation != 'per:employee_of') or (r == 3 and (relation not in ('per:countries_of_residence', 'per:cities_of_residence', 'per:stateorprovinces_of_residence')) or (r == 4 and relation != 'org:top_members/employees')):
            continue
        print("\t\t=== Extracted Relation ===")
        print(f"\t\tInput tokens: {ex['tokens']}")
        extracted += 1
        subj = ex['subj'][0]
        obj = ex['obj'][0]
        confidence = pred[1]
        print(f"\t\tOutput Confidence: {confidence}; Subject: {subj}; Object: {obj};")
        if confidence > t:
            if X[(subj, relation, obj)] < confidence:
                X[(subj, relation, obj)] = confidence
                print("\t\tAdding to set of extracted relations")
                extraction_added += 1
            else:
                print("\t\tDuplicate with lower confidence than existing record, Ignoring this.")
        else:
            print("\t\tConfidence is lower than threshold confidence. Ignoring this.")
        print("\t\t==========")
    return extracted, extraction_added

# Generate response to prompt
def get_gemini_completion(prompt, model_name, max_tokens, temperature, top_p, top_k):

    # Initialize a generative model
    model = genai.GenerativeModel(model_name)

    # Configure the model with your desired parameters
    generation_config=genai.types.GenerationConfig(
        max_output_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k
    )

    # Generate a response
    response = model.generate_content(prompt, generation_config=generation_config)

    return response.text

def run_gemini(sentence, gemini_key, r):
    genai.configure(api_key=gemini_key)
    relationship = None
    subj = None
    obj = None
    if r == 1:
        relationship = "Schools_Attended"
        subj = "person"
        obj = "organization"
    elif r == 2:
        relationship = "Work_For"
        subj = "person"
        obj = "organization"
    elif r == 3:
        relationship = "Live_In"
        subj = "person"
        obj = "location, city, state, province, or country"
    else:
        relationship = "Top_Member_Employees"
        subj = "organization"
        obj = "person"
    prompt_text = f"""Given a sentence, extract the subject and the object with relationship {relationship} in which subject is a {subj} and object is a {obj}. The output should indicate the subject and object separated by a new line in the following format: \n subject: \n object:\n. \n sentence: {sentence} """
    model_name = 'gemini-pro'
    max_tokens = 100
    temperature = 0.2
    top_p = 1
    top_k = 32
    response_text = get_gemini_completion(prompt_text, model_name, max_tokens, temperature, top_p, top_k)
    extracted = 0
    extraction_added = 0
    # interpret the response from gemini
    lines = response_text.split('\n')
    if len(lines) < 2:
        return extracted, extraction_added
    for index, line in enumerate(lines):
        values = line.split(':')
        if len(values) < 2:
            return extracted, extraction_added
        if index == 0:
            subj = values[1].strip()
        else:
            obj = values[1].strip()
    if subj not in ('', ' ') and obj not in ('', ' '):
        extracted += 1
    else:
        return extracted, extraction_added
    print("\t\t=== Extracted Relation ===")
    print(f"\t\tSentence: {sentence}")
    print(f"\t\tSubject: {subj} ; Object: {obj} ;")
    if X[(subj, obj)] < 1:
        X[(subj, obj)] = 1
        extraction_added += 1
        print(f"\t\tAdding to set of extracted relations")
    else:
        print("\t\tDuplicate. Ignoring this.")
    print("\t\t==========")
    return extracted, extraction_added

def process_url(url, url_num, r, model, t, gemini_key, spanbert):
    print(f"\n\nURL ( {url_num+1} / 10 ): {url}")
    # Check if we have processed this url before
    if url in seen_urls:
        print("We have seen this url before. Skipping...")
        return
    seen_urls.add(url)
    print("\tFetching text from url ...")
    # Retrieve the corresponding webpage
    response = requests.get(url)
    # Skip the webpage that cannot be retrieved
    if response.status_code != 200:
        print("Unable to retrieve url. Skipping...")
        return
    # Extract plain text using BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    plain_text = soup.get_text()
    # Truncate the text if too long
    if len(plain_text) > 10000:
        plain_text = plain_text[:10000]
    print(f"\tWebpage length (num characters): {len(plain_text)}")
    print("\tAnnotating the webpage using spacy...")
    # Split the text into sentences 
    nlp = spacy.load("en_core_web_lg")
    doc = nlp(plain_text)
    num_sentences = len([s for s in doc.sents])
    print(f"\tExtracted {num_sentences} sentences. Processing each sentence one by one to check for presence of right pair of named entity types; if so, will run the second pipeline ...")
    # Find required named entities based on user input r
    entities_of_interest = ["PERSON"]
    live_in_obj = ["LOCATION", "CITY", "STATE_OR_PROVINCE", "COUNTRY"]
    if r in (1,2,4):
        entities_of_interest.append("ORGANIZATION")
    else:
        entities_of_interest.extend(live_in_obj)
    # sentence_extracted is the number of sentences that we extracted annotations from
    sentence_extracted = 0
    # website_extracted is the total number of extractions we had on current website
    website_extracted = 0
    # website_extraction_added is the number of extractions we added to X from current website
    website_extraction_added = 0
    for i, sentence in enumerate(doc.sents):
        entity_pairs = create_entity_pairs(sentence, entities_of_interest)
        # examples are all entity pairs that have relationships we are interested in
        examples = []
        # extracted is the number of extractions we had on current sentence
        extracted = 0
        # extraction_added is the number of extractions we added to X from current sentence
        extraction_added = 0
        # check if the relationship match the input r
        for ep in entity_pairs:
            if r == 3:
                if "PERSON" not in [ep[1][1], ep[2][1]] or (ep[2][1] not in live_in_obj and ep[1][1] not in live_in_obj):
                    continue
                if ep[1][1] == "PERSON":
                    examples.append({"tokens": ep[0], "subj": ep[1], "obj": ep[2]})
                else:
                    examples.append({"tokens": ep[0], "subj": ep[2], "obj": ep[1]})
            else:
                if "PERSON" not in [ep[1][1], ep[2][1]] or "ORGANIZATION" not in [ep[1][1], ep[2][1]]:
                    continue
                if r == 4:
                    if ep[1][1] == "ORGANIZATION":
                        examples.append({"tokens": ep[0], "subj": ep[1], "obj": ep[2]})
                    else:
                        examples.append({"tokens": ep[0], "subj": ep[2], "obj": ep[1]})
                else:
                    if ep[1][1] == "PERSON":
                        examples.append({"tokens": ep[0], "subj": ep[1], "obj": ep[2]})
                    else:
                        examples.append({"tokens": ep[0], "subj": ep[2], "obj": ep[1]})
        if (i + 1) % 5 == 0:
            print(f"\tProcessed {i+1} / {num_sentences} sentences")
        if len(examples) == 0:
            continue
        if model == "spanbert":
            extracted, extraction_added = run_spanbert(examples, t, spanbert, r)
        else:
            extracted, extraction_added = run_gemini(sentence, gemini_key, r)
        if extracted > 0:
            sentence_extracted += 1
        website_extracted += extracted
        website_extraction_added += extraction_added
        
    print(f"\tExtracted annotations for {sentence_extracted} out of total {num_sentences} sentences")
    print(f"\tRelations extracted from this website: {website_extraction_added} (Overall: {website_extracted})")


def loop(user_input):
    # i is the current number of iterations
    i = 0
    model, api_key, engine_id, gemini_key, r, t, q, k = user_input
    # Keep track of the queries we have used so far in each iteration
    query_used = {q}
    spanbert = None
    if model == "spanbert":
        spanbert = SpanBERT("./pretrained_spanbert")
    
    while True:
        # Retrieve the top 10 results for the query from Google 
        res = search(api_key, engine_id, q)
        user_input[6] = q
        print_param(user_input, i)
        # j is the current number of url
        for j in range(10):
            url = res['items'][j]['formattedUrl']
            process_url(url, j, r, model, t, gemini_key, spanbert)
        i += 1
        if r == 1:
            relationship = "Schools_Attended"
        elif r == 2:
            relationship = "Work_For"
        elif r == 3:
            relationship = "Live_In"
        else:
            relationship = "Top_Member_Employees"
        if model == 'spanbert':
            sorted_X = sorted(X.items(), key=lambda item: item[1], reverse=True)
            if len(X) >= k:
                print(f"================== ALL RELATIONS for {relationship} ( {len(X)} ) ==================")
                for x in sorted_X:
                    print(f"Confidence: {x[1]}\t| Subject: {x[0][0]}\t| Object: {x[0][2]}")
                print(f"Total # of iterations = {i}")
                break
            else:
                query_found = False
                for x in sorted_X:
                    potential_query = x[0][0] + ' ' + x[0][2]
                    if potential_query not in query_used:
                        q = potential_query
                        query_found = True
                        query_used.add(potential_query)
                        break
                

        else:
            if len(X) >= k:
                print(f"================== ALL RELATINOS for {relationship} ( {len(X)} ) ==================")
                for x in X:
                    print(f"Subject: {x[0]}\t| Object: {x[1]}")
                print(f"Total # of iterations = {i}")
                break
            else:
                query_found = False
                for x in X:
                    potential_query = x[0] + ' ' + x[1]
                    if potential_query not in query_used:
                        q = potential_query
                        query_found = True
                        query_used.add(potential_query)
                        break
        if not query_found:
            print("ISE has stalled before retrieving k high-confidence tuples")
            break


def main():
    user_input = get_query()

    loop(user_input)


if __name__ == "__main__":
    main()
