# generative_fiction
Generate a novel work of fiction from a prompt

## Sample Code:

```python
import logging
import httpimport
# next three imports speed up loading...
print(
  "Loading Generative Fiction Module...")
import time
import openai
import traceback
with httpimport.github_repo('georgemcarlson', 'generative_fiction', ref='main'):
  import generative_fiction

# Constants
theApiKey = "the_api_key_to_use"
pathToDocDir = "/the/path/to/log/to/"

def getArgs():
  prompt = "Please write a high-level outline for a book. Include a list of characters and a short description of each character. Include a list of chapters and a short summary of what happens in each chapter. You can pick any title and genre you want."
  fantasyAuthor = {
    "temp": 1,
    "descr": "You are an aspiring author trying to write a fantasy genre fan fiction book. The prose you write in is inspired by modern-day fantasy genere authors such as Patrick Rothfuss and George R. R. Martin.",
    "respExclusion": [
      "Patrick Rothfuss"
      "Rothfuss",
      "George R. R. Martin",
      "George Martin"
      ]
  }
  # Create a custom logger
  bookLogger = logging.getLogger("book")
  bookLogger.setLevel(logging.DEBUG)
  # Log book contents and cost to console
  c_handler = logging.StreamHandler()
  c_handler.setLevel(logging.WARNING)
  bookLogger.addHandler(c_handler)
  # Log WARNING to external file
  f_handler = logging.FileHandler(
    pathToDocDir + "book.log.warning.txt", 
    mode = "w"
  )
  f_handler.setLevel(logging.WARNING)
  bookLogger.addHandler(f_handler)
  # Log DEBUG to external file
  d_handler = logging.FileHandler(
    pathToDocDir + "book.log.debug.txt", 
    mode = "w"
  )
  d_handler.setLevel(logging.DEBUG)
  bookLogger.addHandler(d_handler)
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
  return {
    "apiKey": theApiKey,
    "gpt40Enabled": True,
    "firstPerson": True,
    "author": fantasyAuthor,
    #"prompt": dosPrompt 
    #"prompt": notwPrompt,
    "prompt": prompt,
    "gradeLevel": 10,
    "perspective": "first-person",
    "logger": bookLogger,
  }

print("Begin Writing Book...")
generative_fiction.main(getArgs())
```