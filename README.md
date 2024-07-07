# Web Information Extraction with SpanBERT and Gemini

Web-Information-Extraction-with-SpanBERT-and-Gemini

# Team Members
Ronitt Mehra (UNI: rm4084) <br>
Yueran Ma (UNI: ym2876)

# Steps to run the program
`git clone https://github.com/Ronitt272/Enhanced-Information-Retrieval-System-with-Query-Expansion.git` <br>
`cd Enhanced-Information-Retrieval-System-with-Query-Expansion` <br>
`pip3 install -r requirements.txt` <br>
`pip3 install -q -U google-generativeai` <br>
`pip3 install --upgrade google-api-python-client`  <br>
`pip3 install beautifulsoup4` <br>
`pip3 install -U pip setuptools wheel` <br>
`pip3 install -U spacy` <br>
`python3 -m spacy download en_core_web_lg` <br>
`python3 project2.py [-spanbert|-gemini] <google api key> <google engine id> <google gemini api key> <r> <t> <q> <k>` <br>

- r --> an integer between 1 and 4, indicating the relation to extract: 1 is for Schools_Attended, 2 is for Work_For, 3 is for Live_In, and 4 is for Top_Member_Employees. <br>
- t --> is a real number between 0 and 1, indicating the "extraction confidence threshold," which is the minimum extraction confidence that we request for the tuples in the output; t is ignored if we are specifying -gemini. <br>
- q --> is a "seed query," which is a list of words in double quotes corresponding to a plausible tuple for the relation to extract (e.g., "bill gates microsoft" for relation Work_For). <br>
- k --> is an integer greater than 0, indicating the number of tuples that we request in the output. <br>

# Internal Design

When the program is called, it first gets the user's input as command line arguments, and then start the loop() function.
In each iteration of the loop function, we retrieve the top 10 results for the provided query using the Google Search API, and process each url with the process_url() function.
For each url, we extract the plain text using BeautifulSoup, split the text into sentences and obtain all entity pairs of our interest, based on input 'r' using SpaCy. Then we call either the run_spanbert() function or the run_gemini() function depending on the user's input.
In run_spanbert() function, we predict the relation between each entity pair and add it to the set X, if the confidence is high enough (which simply means if the confidence is higher than the confidence threshold provided by the user as input).
In run_gemini() function, we create the prompt based on the current sentence and add the response from gemini to set X.
Then we go back to the process_url() function, and keep track of all the extracted entity pairs added to X
Finally, we go back to the loop() function, and check whether we have enough entity pairs extracted in X. If we
have more than or equal to 'k' entity pairs extracted in X, then we display all the entity pairs, and end the program. If we have less than 'k' entity pairs extracted in X, then we call another iteration, by again searching for the top 10 results using the Google Search API.

# Extraction of Relations from Webpages Using BeautifulSoup, spaCy, and SpanBERT/Gemini

In process_url() function, first we check if we have processed this url before. If so, we skip this url.
Then we retrieve the corresponding webpage from the url. We skip this url if returned status code is not 200.
We then extract plain text of the webpage using BeautifulSoup. We truncate the text to 10000 characters if it is any longer than that. Then, we split the text into sentences using SpaCy. We also need to have of list of entities_of_interest based on user input 'r'.
Then we initialize some variables to keep track of the number of sentences that we extract annotations from, the number of extractions we had on current website, and the number of extractions that we successfully added to X from current website.
For each sentence, we first create all entity pairs. Then for each entity pair, we check if the subject and object match the relation we are interested in. We save all entity pairs we are interested in in the examples list.
If -spanbert is specified, we run spanbert using examples list.
 
Spanbert provides us the predicted relationship for each entity pair. We only consider the ones with the correct relationship and high enough confidence level (confidence level above the threshold provided by the user). We ignore the ones with confidence lower than threshold 't' or the ones that are duplicated and with lower confidence than existing record. If -gemini is specified, we run gemini using the sentence if examples list is not empty. We create a prompt based on the required relation, subject, object, and the sentence. We specify the output format in the prompt so that we can split the output using keyword and interpret them. We add all outputs that are not empty to X.





