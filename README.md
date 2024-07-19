# Overview:
Generate a full-length work of fiction from a prompt to write a high-level outline for a book.

## Credits:

Based on Chiara Coetzee's research into "[Generating a full-length work of fiction with GPT-4](#https://medium.com/@chiaracoetzee/generating-a-full-length-work-of-fiction-with-gpt-4-4052cfeddef3)"

## Sample Code:

Generate a whole book in one go. Supply a custom logger to write the book contents to a file.

```python
import logging
import generative_fiction

# Constants
theApiKey = "the_api_key_to_use"
pathToDocDir = "/the/path/to/log/to/"
thePrompt = """Please write a high-level outline for a book. Include a list of characters and a short description of each character. Include a list of chapters and a short summary of what happens in each chapter. You can pick any title and genre you want."""
authorTemp = 0.95
authorDescr = """You are an aspiring author trying to write a fantasy genre fan fiction book. The prose you write in is inspired by modern-day fantasy genere authors such as Patrick Rothfuss and George R. R. Martin."""
authorExclusions = [
  "Patrick Rothfuss"
  "Rothfuss",
  "George R. R. Martin",
  "George Martin"]
# Create a custom logger
bookLogger = logging.getLogger("book")
bookLogger.setLevel(logging.DEBUG)
# Log book contents and cost to console
c_handler = logging.StreamHandler()
c_handler.setLevel(logging.WARNING)
bookLogger.addHandler(c_handler)
# Log book contents to external file
# Note:
#   All the book's contents
#   are logged as CRITICAL
b_handler = logging.FileHandler(
  pathToDocDir + "book.txt", 
  mode = "w"
)
b_handler.setLevel(logging.CRITICAL)
bookLogger.addHandler(b_handler)
# write the book
print("Begin Writing Book...")
generative_fiction.GenerativeFiction(
  apiKey=theApiKey,
  authorTemp=authorTemp,
  authorDescr=authorDescr,
  authorRespExclusions=authorExclusions,
  prompt=thePrompt,
  gradeLevel=10,
  logger=bookLogger
).writeBook()
```

Generate a book one chapter at a time. Save the books state after each generated chapter. Will allow for re-generating chapters. Good for generating a chapter, proof-reading to make sure it's a "keeper", and then moving on to the next chapter.

```python
import generative_fiction
import json

# Constants
theApiKey = "the_api_key_to_use"
pathToDocDir = "/the/path/to/log/to/"
thePrompt = """Please write a high-level outline for a book. Include a list of characters and a short description of each character. Include a list of chapters and a short summary of what happens in each chapter. You can pick any title and genre you want."""
authorDesc="""You are an aspiring author trying to write a fantasy genre fan fiction book."""

# Configure generative_fiction
gf = generative_fiction.GenerativeFiction(
  apiKey=theApiKey,
  largeModel=False,
  authorDescr=authorDesc,
  authorTemp=0.95,
  prompt=thePrompt,
  gradeLevel=10
)
book = {}
# load save state from file if it exists
try:
  f = open(pathToDocDir + 'book.json') 
  book = json.load(f)
  f.load()
except:
  # no save state exists; start new book
  book["theEnd"] = False
# generate the book
print("Begin Generating Book...")
chStart=1
if "chapters" in book:
  chStart=len(book["chapters"]) + 1
chEnd = chStart + 1
for chNum in range(chStart, chEnd):
  if book["theEnd"]:
    break
  book = gf.writeChapter(chNum, book)
  # save state to a file after each chapter
  f = open(pathToDocDir + 'book.json', 'w')
  json.dump(book, f)
  f.close()
# write the content to a file
content = book["title"]
chapters = book["chapters"]
sceneDivider="\n\n* * *\n\n"
for i in range(0, len(chapters)):
  chNum=i+1
  content=content+"\n\n\n\n\n"
  content=content+"Chapter "+str(chNum)
  content=content+"\n\n\n\n\n"
  chapter=chapters["ch" + str(chNum)]
  divider=sceneDivider
  scenes=divider.join(chapter["scenes"])
  content=content+scenes
if book["theEnd"]:
  content=content+"\n\n\n\n\nThe End."
f = open(pathToDocDir + "book.txt", "w")
f.write(content)
f.close()
```