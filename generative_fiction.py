import re
import time
import logging
import json
import urllib.request

# https://medium.com/@chiaracoetzee/generating-a-full-length-work-of-fiction-with-gpt-4-4052cfeddef3

chatModels = {
  "gpt35": {
    "id": "gpt-3.5-turbo",
    "pricing": {
      "input": (0.5 / 1000000),
      "output": (1.5 / 1000000)
    }
  },
  "gpt40": {
    "id": "gpt-4o",
    "pricing": {
      "input": (5 / 1000000),
      "output": (15 / 1000000)
    }
  }
}

defAuthor = {
  "temp": 0.95,
  "descr": """You are an aspiring author trying to write a fan-fiction book ."""
}

helpfulAssistant = {
  "temp": .8,
  "descr": """You are a helpful assistant."""
}

defLogger = logging.getLogger("default")

book = {}
settings =  {}

class GenerativeFiction:
  apiKey: str
  gpt40Enabled: bool
  author: dict
  prompt: str
  gradeLevel: int
  logger: logging.Logger
  
  # class constructor
  def __init__(
    self,
    apiKey: str = None,
    gpt40Enabled: bool = True,
    authorDescr: str = defAuthor["descr"],
    authorTemp: float = defAuthor["temp"],
    authorRespExclusions: list[str] = None,
    prompt: str = None,
    gradeLevel: int = 10,
    logger: logging.Logger = defLogger):
    self.apiKey=apiKey
    self.gpt40Enabled=gpt40Enabled
    author = {
      "descr": authorDescr,
      "temp": authorTemp}
    if authorRespExclusions is not None:
      exclusions = authorRespExclusions
      author["respExclusion"] = exclusions
    self.author = author
    self.prompt = prompt
    self.gradeLevel = gradeLevel
    self.logger = logger

  def writeBook(self):
    theBook = {}
    theBook["theEnd"] = False
    # using a while loop because the total
    #   number of chapters can change over
    #   time.
    while not theBook["theEnd"]:
      chNum = 1
      if "chapters" in theBook:
        chNum = len(theBook["chapters"]) + 1
      theBook = self.writeChapter(
        chNum=chNum,
        save=theBook)
    return theBook.copy()

  def writeChapter(
    self,
    chNum: int,
    save: dict,
    firstPerson: bool = False):
    loadSettings(
      apiKey=self.apiKey,
      gpt40Enabled=self.gpt40Enabled,
      firstPerson=firstPerson,
      author=self.author,
      gradeLevel=self.gradeLevel,
      logger=self.logger
    )
    book.clear()
    book["continuity"] = ""
    book["theEnd"] = False
    book["chapters"] = {}
    if chNum == 0:
      return book.copy()
    elif chNum == 1:
      initOutlinePrompt = self.prompt
      initLvl1Notes(initOutlinePrompt)
    else:
      debug("Loading Save State...")
      loadSaveState(chNum, save)
    if book["theEnd"]:
      critical(p(p(p("The End"))))
      return book.copy()
    info("Writing next chapter:")
    critical(
      p(p(p("Chapter: " + str(chNum)))))
    if isLastCh(chNum):
      outlineFinalChapter()
    else:
      outlineChapter(chNum)
    wordRangeLow = 250 * self.gradeLevel,
    wordRangeHigh = 350 * self.gradeLevel,
    chDraft = getChatAuthorResp(
      '''Ch {chNum} 1st Draft'''.format(
        chNum = chNum
      ),
      [
        getOutlinePrompt(),
        getOutline(),
        getProtagionistPrompt(),
        getProtagionist(),
        getChCharDescsPrompt(chNum),
        getChCharDescs(chNum),
        getChChronoPrompt(chNum),
        getChChrono(chNum),
        getChOutlinePrompt(chNum),
        getChOutline(chNum),
        getChContinuityPrompt(chNum),
        getChContinuity(chNum),
        '''Write a final draft of Chapter {chNum}. Use the following guidance:
  
  Begin the final draft with the beginning of the first scene of Chapter {chNum}. Only include the contents of the scenes in the final draft of Chapter {chNum}. Seperate each scene with '\n\n***\n\n'. Finish the final draft immediately after the ending of the last scene of Chapter {chNum}.
  
  The final draft of Chapter {chNum} should set up the story for Chapter {nextChNum}, which will come immediately afterwards.
  
  Make sure that the chapter contains between {wordRangeLow} and {wordRangeHigh} words.
  
  Make sure to use a 'Show, dont tell' technique to show drama unfold on the page and place {protagionist}, the main charater, at the center of the story.
  
  Make sure to use vivid and specific details to make descriptions more interesting and memorable. Avoid generic and clichéd descriptions. 
  
  Make sure to be concise. Avoid long and drawn-out descriptions that slow down the pace of the story. Instead, choose specific details that are most important to the scene and use them to convey the desired mood or atmosphere.
  
  Make sure to write in an engaging narrative style.
  
  Make sure that the chapter is rewritten to a {gradeLevel} grade reading level.'''.format(
          wordRangeLow=wordRangeLow,
          wordRangeHigh=wordRangeHigh,
          protagionist = getProtagionist(),
          chNum = chNum,
          nextChNum = chNum + 1,
          gradeLevel = self.gradeLevel
        )
      ]
    )
    info("Ch Draft:\n\n" + chDraft)
    chDraftScenes = parseScenes(chDraft)
    sceneCount = countScenes(
      chNum,
      chDraftScenes
    )
    chOutline = ""
    for i in range(int(sceneCount)):
      sceneDraft = chDraftScenes[i].strip()
      sceneOutline = getChatAssistantResp(
        "Return scenes outline",
        [
      '''Write a detailed outline of the following scene:"
  
  ```
  {sceneDraft}
  ```'''.format(
          sceneDraft = sceneDraft)
        ])
      chOutline += '''
  
  Scene {sceneNum}:
  {sceneOutline}'''.format(
        sceneNum=i+1,
        sceneOutline=sceneOutline.strip()
      )
    setChOutline(chNum, chOutline.strip())
    wordRangeLow = 250 * self.gradeLevel
    wordRangeHigh = 350 * self.gradeLevel
    chDraft = getChatAuthorResp(
      '''Ch {chNum} 2nd Draft'''.format(
        chNum = chNum
      ),
      [
        getOutlinePrompt(),
        getOutline(),
        getProtagionistPrompt(),
        getProtagionist(),
        getChCharDescsPrompt(chNum),
        getChCharDescs(chNum),
        getChChronoPrompt(chNum),
        getChChrono(chNum),
        getChOutlinePrompt(chNum),
        getChOutline(chNum),
        getChContinuityPrompt(chNum),
        getChContinuity(chNum),
        '''Write a final draft of Chapter {chNum}. Use the following guidance:
  
  Begin the final draft with the beginning of the first scene of Chapter {chNum}. Only include the contents of the scenes in the final draft of Chapter {chNum}. Seperate each scene with '\n\n***\n\n'. Finish the final draft immediately after the ending of the last scene of Chapter {chNum}.
  
  The final draft of Chapter {chNum} should set up the story for Chapter {nextChNum}, which will come immediately afterwards.
  
  Make sure that the chapter contains between {wordRangeLow} and {wordRangeHigh} words.
  
  Make sure to use a 'Show, dont tell' technique to show drama unfold on the page and place the main charater at the center of the story.
  
  Make sure to use vivid and specific details to make descriptions more interesting and memorable. Avoid generic and clichéd descriptions. 
  
  Make sure to be concise. Avoid long and drawn-out descriptions that slow down the pace of the story. Instead, choose specific details that are most important to the scene and use them to convey the desired mood or atmosphere.
  
  Make sure to write in an engaging narrative style.
  
  Make sure that the chapter is rewritten to a {gradeLevel} grade reading level.'''.format(
          wordRangeLow = wordRangeLow,
          wordRangeHigh = wordRangeHigh,
          chNum = chNum,
          nextChNum = chNum + 1,
          gradeLevel = self.gradeLevel
        )
      ]
    )
    setChDraft(chNum, chDraft)
    chDraftScenes = parseScenes(chDraft)
    sceneCount = countScenes(
      chNum,
      chDraftScenes
    )
    scenes = []
    for i in range(int(sceneCount)):
      scene = writeScene(
        chNum,
        i+1,
        chDraftScenes)
      scenes.append(scene)
      if i > 1:
        critical(p("* * *"))
      critical(p(scene))
    saveChapter(chNum, scenes)
    return book.copy()

def parseScenes(chDraft):
  chDraftScenes = chDraft.split("***")
  cleanChDraftScenes = []
  for scene in chDraftScenes:
    if len(scene) < 50:
      continue
    if "." not in scene:
      continue
    if scene.strip().startswith("Chapter"):
      continue
    cleanChDraftScenes.append(scene)
  return cleanChDraftScenes

def countScenes(chNum, chDraftScenes):
  sceneCount = getChatIntResp(
    '''Count Ch {chNum} Scenes'''.format(
      chNum = chNum
    ),
    [
      '''Count and return as an integer the total number of scenes in the following chapter:

```
{chDraft}
```'''.format(
        chDraft="***".join(chDraftScenes)
      )
    ]
  )
  if sceneCount < 2:
    sceneCount = len(chDraftScenes)
  elif sceneCount > len(chDraftScenes):
    sceneCount = len(chDraftScenes)
  info('''Ch {chNum} scene count: {sceneCount}'''.format(
    chNum = chNum,
    sceneCount = sceneCount
  ))
  return sceneCount

def rewriteScene(chNum, sceneNum, chDraftScenes):
  sceneCount = len(chDraftScenes)
  chLen = getTargetChapterLength()
  sceneLen= chLen / sceneCount
  sceneDraft = chDraftScenes[sceneNum - 1].strip()
  if getGradeLevelAsInt() < 4:
    return sceneDraft
  firstParagraph = getChatAssistantResp(
    '''Scene {sceneNum}: First Para'''.format(sceneNum=sceneNum),
    [
      '''Return only the first opening paragraph of the following scene:

```
{sceneDraft}
```'''.format(
    sceneDraft = sceneDraft)
  ])
  info("First Opening paragraph:\n\n"+firstParagraph)
  lastParagraph = getChatAssistantResp(
    '''Scene {sceneNum}: Last Para'''.format(sceneNum=sceneNum),
    [
      '''Return only the last final paragraph of the following scene:"

```
{sceneDraft}
```'''.format(
    sceneDraft = sceneDraft)
  ])
  info("Last Final paragraph:\n\n" + lastParagraph)
  qualityControlPrompt = '''Please rewrite Scene {sceneNum} for Chapter {chNum} of my book to be a longer more detailed version. Use the following guidance:

Please make sure that you reuse at least 60% of the words in the original scene's text.

Make sure that the total number of sentences in your rewrite at least matches the number of sentences in the original scene's text.

Make sure that the total number of paragraphs in your rewrite at least matches the number of paragraphs in the original scene's text.

Make sure to use a 'Show, dont tell' technique to show drama unfold on the page and place the main charater at the center of the story.

Make sure to use vivid and specific details to make descriptions more interesting and memorable. Avoid generic and clichéd descriptions. 

Make sure to be concise. Avoid long and drawn-out descriptions that slow down the pace of the story. Instead, choose specific details that are most important to the scene and use them to convey the desired mood or atmosphere.

Make sure to write in an engaging narrative style.

Make sure that the scene is rewritten to a {gradeLevel} grade reading level.

Make sure to start with the scene's first opening paragraph.

Make sure to finish with the scene's last closing paragraph.

Make sure to only write one scene.
'''.format(
    sceneNum=sceneNum,
    chNum=chNum,
    gradeLevel=getGradeLevelAsStr()
  )
  for _ in range(4):
    scene = getChatAuthorResp(
      "Rewrite Scene " + str(sceneNum),
      [
        getChCharDescsPrompt(chNum),
        getChCharDescs(chNum),
        getChChronoPrompt(chNum),
        getChChrono(chNum),
        getChOutlinePrompt(chNum),
        getChOutline(chNum),
        getChContinuityPrompt(chNum),
        getChContinuity(chNum),
        '''Please write Scene {sceneNum} for Chapter {chNum} of my book.'''.format(
          sceneNum=sceneNum,
          chNum=chNum
        ),
        sceneDraft,
        '''Return the first paragraph from Chapter {chNum} Scene {sceneNum} of my book.'''.format(
          sceneNum=sceneNum,
          chNum=chNum
        ),
        firstParagraph,
        '''Return the last paragraph from Chapter {chNum} Scene {sceneNum} of my book.'''.format(
          sceneNum=sceneNum,
          chNum=chNum
        ),
        lastParagraph,
        qualityControlPrompt
      ]
    )
    debug("QC Scene:\n\n" + scene)
    if len(scene) < float(len(sceneDraft)) * 0.9:
      continue
    if not "\n" in scene.strip():
      continue
    if ("request" and "generat") in scene:
      continue
    if len(scene) < float(sceneLen) * 0.9:
      continue
    sceneDraft = scene
    break
  return sceneDraft
  
def writeScene(
  chNum,
  sceneNum,
  chDraftScenes):
  scene = rewriteScene(
    chNum,
    sceneNum,
    chDraftScenes
  )
  sceneContinuityNotesPrompt = '''Please briefly note any important details or facts from Scene {sceneNum} that you need to remember while writing the rest of Chapter {chNum} of my book, in order to ensure continuity and consistency throughout the chapter. Begin the continuity notes with the first continuity note from Scene {sceneNum}. Only include the continuity notes for Scene {sceneNum} in your response.

Continuity Notes:'''.format(
    chNum=chNum,
    sceneNum=sceneNum
  )
  sceneContinuity=getChatAssistantResp(
    "Scene Continuity Notes",
    [
      getOutlinePrompt(),
      getOutline(),
      getProtagionistPrompt(),
      getProtagionist(),
      getChCharDescsPrompt(chNum),
      getChCharDescs(chNum),
      getChChronoPrompt(chNum),
      getChChrono(chNum),
      getChDraftPrompt(chNum),
      getChDraft(chNum),
      getContinuityPrompt(),
      getContinuity(),
      getScenePrompt(chNum, sceneNum),
      scene,
      sceneContinuityNotesPrompt
    ]
  )
  updatedChContinuity = '''{chContinuity}

Scene {sceneNum} Continuity Notes:

{sceneContinuity}
  '''.format(
    chContinuity = getChContinuity(chNum),
    sceneNum = sceneNum,
    sceneContinuity = sceneContinuity
  )
  setChContinuity(
    chNum,
    updatedChContinuity
  )
  if getPerspective() == "first-person":
    scene = rewriteInFirstPerson(scene)
  return scene
  
def outlineFinalChapter():
  chNum = getChCount()
  updateChChrono(chNum)
  finalChContinuityPrompt = '''Please briefly note any important details or facts from this book's Continuity Notes that you will need to remember while writing the Final Chapter of my book, in order to ensure continuity and consistency. Label these Continuity Notes. Make sure to remember that the Final Chapter of my book will conclude my book.'''
  finalChCharDescsPrompt = '''Please print out a list of my book's relevant characters, with short descriptions, that you will need to know about to write the Final Chapter of my book taking into consideration my book's high-level outline, characters and notable items, Chronology, Continuity Notes. Also list any notable items or objects in the story, with short descriptions, that you will need to know about to write the Final Chapter of my book. Make sure to remember that the Final Chapter of my book will conclude my book.'''
  finalChOpeningScenePrompt = '''For the Final Chapter of my book, please write a detailed outline describing the first, opening scene taking into consideration my book's high-level outline, relevant characters and notable items, Chronology, and Continuity Notes. It should describe what happens in that opening scene and set up the story for the rest of the book. Do not summarize the entire chapter, only the first scene. The opening scene of the Final Chapter should directly follow the final scene of Chapter {prevChNum}'''.format(
    prevChNum = chNum -1
  )
  finalChFinalScenePrompt = '''For the Final Chapter of my book, write a detailed outline describing the final, last scene of the chapter taking into consideration my book's high-level outline, relevant characters and notable items, Chronology, and Continuity Notes. It should describe what happens at the very end of the chapter, and conclude the book.'''
  finalChOutlinePrompt = '''For the Final Chapter of my book, write a detailed chapter outline taking into consideration my book's high-level outline, relevant characters and notable items, Chronology, Continuity Notes, and the Opening and Final scenes for the Final Chapter. The chapter outline must list all the scenes in the chapter and a short description of each. Begin the chapter outline with the Opening Scene from the Final Chapter, and finish the outline with the Final Scene from the Final Chapter. This chapter outline must conclude the book.'''
  chat = [
    getOutlinePrompt(),
    getOutline(),
    getProtagionistPrompt(),
    getProtagionist(),
    getCharDescsPrompt(),
    getCharDescs(),
    getChChronoPrompt(chNum),
    getChChrono(chNum),
    getContinuityPrompt(),
    getContinuity(),
    finalChContinuityPrompt
  ]
  setChContinuity(
    chNum,
    getChatAssistantResp(
      "Final Ch Continuity",
      chat
    )
  )
  chat.extend([
    getChContinuity(chNum),
    finalChCharDescsPrompt
  ])
  setChCharDescs(
    chNum,
    getChatAssistantResp(
      "Final Ch Char Descrs",
      chat
    )
  )
  chOpenScene = getChatAssistantResp(
    "Final Ch Opening Scene",
    [
      getOutlinePrompt(),
      getOutline(),
      getProtagionistPrompt(),
      getProtagionist(),
      finalChCharDescsPrompt,
      getChCharDescs(chNum),
      getChChronoPrompt(chNum),
      getChChrono(chNum),
      finalChContinuityPrompt,
      getChContinuity(chNum),
      finalChOpeningScenePrompt
    ]
  )
  chFinalScene = getChatAssistantResp(
    "Final Ch Final Scene",
    [
      getOutlinePrompt(),
      getOutline(),
      getProtagionistPrompt(),
      getProtagionist(),
      finalChCharDescsPrompt,
      getChCharDescs(chNum),
      getChChronoPrompt(chNum),
      getChChrono(chNum),
      finalChContinuityPrompt,
      getChContinuity(chNum),
      finalChOpeningScenePrompt,
      chOpenScene,
      finalChFinalScenePrompt
    ]
  )
  setChOutline(
    chNum,
    getChatAssistantResp(
      "Final Ch Outline",
      [
        getOutlinePrompt(),
        getOutline(),
        getProtagionistPrompt(),
        getProtagionist(),
        finalChCharDescsPrompt,
        getChCharDescs(chNum),
        getChChronoPrompt(chNum),
        getChChrono(chNum),
        finalChContinuityPrompt,
        getChContinuity(chNum),
        finalChOpeningScenePrompt,
        chOpenScene,
        finalChFinalScenePrompt,
        chFinalScene,
        finalChOutlinePrompt
      ]
    )
  )
  
def outlineChapter(chNum):
  updateChChrono(chNum)
  setBoundingScenes(chNum)
  chat = [
    getOutlinePrompt(),
    getOutline(),
    getProtagionistPrompt(),
    getProtagionist(),
    getContinuityPrompt(),
    getContinuity(),
    getCharDescsPrompt(),
    getCharDescs(),
    getChChronoPrompt(chNum),
    getChChrono(chNum),
    getChContinuityPrompt(chNum)
  ]
  setChContinuity(
    chNum,
    getChatAssistantResp(
      '''Ch {chNum} Continuity'''.format(
        chNum = chNum
      ),
      chat
    )
  )
  chat.extend([
    getChContinuity(chNum),
    getChCharDescsPrompt(chNum)
  ])
  setChCharDescs(
    chNum,
    getChatAssistantResp(
      '''Ch {chNum} Char Descs'''.format(
        chNum = chNum
      ),
      chat
    )
  )
  chat = [
    getOutlinePrompt(),
    getOutline(),
    getProtagionistPrompt(),
    getProtagionist(),
    getChCharDescsPrompt(chNum),
    getChCharDescs(chNum),
    getChChronoPrompt(chNum),
    getChChrono(chNum),
    getChOpeningScenePrompt(chNum),
    getChOpeningScene(chNum),
    getChFinalScenePrompt(chNum),
    getChFinalScene(chNum),
    getChContinuityPrompt(chNum),
    getChContinuity(chNum),
    '''For Chapter {chNum} of my book, write a detailed chapter outline taking into consideration my book's high-level outline, relevant characters and notable items, Chronology, Continuity Notes, and the Opening and Final scenes for Chapter {chNum}. The chapter outline must list all the scenes in the chapter and a short description of each. Begin the chapter outline with the Opening Scene from Chapter {chNum}, and finish the outline with the Final Scene from Chapter {chNum}.'''.format(
      chNum = chNum
    )
  ]
  setChOutline(
    chNum,
    getChatAssistantResp(
      '''Ch {chNum} Outline'''.format(
        chNum = chNum
      ),
      chat
    )
  )

def initLvl1Notes(initOutlinePrompt):
  info("""Setting prompt to write the high-level book outline to:

""" + initOutlinePrompt)
  chat = [initOutlinePrompt]
  outline = getChatAuthorResp(
    "Init Outline",
    chat
  )
  initOutline(outline)
  chat.append(outline)
  updateChCount()
  chat.append('''Taking into consideration my book's High-Level Outline, write a list of all the characters in my book. For each listed character include a short description of them and note where in the story they appear. Also list any notable items or objects in the story, with short descriptions.''')
  setCharDescsInit(
    getChatAssistantResp(
      "Init Char Descrs",
      chat
    )
  )
  initProtagionist(
    getChatAssistantResp(
      "Init Protagionist",
      [
        getOutlinePrompt(),
        getOutline(),
        getCharDescsPrompt(),
        getCharDescs(),
        '''What is the name of my book's protagionist, taking into consideration my book's High-Level Outline and Character Descriptions. Only return the name of my books protagionist.'''
      ]
    ).strip()
  )
  initTitle()
  
def setBoundingScenes(chNum):
  chCount = getChCount()
  openingScenePrompt = "For Chapter " + str(chNum) + " of my book, please write a detailed chapter outline describing the first, opening scene taking into consideration my book's high-level outline, characters and notable items, Chronology, and Continuity Notes. It should describe what happens in that opening scene and set up the story for the rest of the chapter. Do not summarize the entire chapter, only the first scene."
  if chNum > 1:
    openingScenePrompt += "The opening scene of Chapter " + str(chNum) + " should directly follow the final scene of Chapter " + str(chNum - 1)
  finalScenePrompt = "For Chapter " + str(chNum) + " of my book, please write a detailed chapter outline describing the final scene of Chapter " + str(chNum) + " taking into consideration my book's high-level outline, characters and notable items, Chronology, and Continuity Notes. It should describe what happens at the very end of the chapter, and set up the story for the opening scene of the next chapter, which will come immediately afterwards. Do not summarize the entire chapter, only the final scene."
  if chNum < chCount:
    finalScenePrompt += "The final scene of Chapter " + str(chNum) + " should directly proceed the opening scene of Chapter " + str(chNum + 1)
  chat = [
    getOutlinePrompt(),
    getOutline(),
    getProtagionistPrompt(),
    getProtagionist(),
    getContinuityPrompt(),
    getContinuity(),
    getCharDescsPrompt(),
    getCharDescs(),
    getChChronoPrompt(chNum),
    getChChrono(chNum),
    openingScenePrompt
  ]
  for i in range(4):
    action = '''Ch {chNum} Opening Scene'''.format(
      chNum = chNum
    )
    if i > 0:
      action = "Rewrite " + action
    openingScene = getChatAssistantResp(
      action,
      chat + [openingScenePrompt]
    )
    if len(openingScene) > 100:
      setChOpeningScene(
        chNum,
        openingScene
      )
      break
  for i in range(4):
    action = '''Ch {chNum} Final Scene'''.format(
      chNum = chNum
    )
    if i > 0:
      action = "Rewrite " + action
    finalScene = getChatAssistantResp(
      action,
      chat + 
      [
        getChOpeningScene(chNum),
        finalScenePrompt
      ]
    )
    if len(finalScene) > 100:
      setChFinalScene(
        chNum,
        finalScene
      )
    break

def condenseContinuityNotes():
  if settings["gpt40Enabled"]:
    info("Skip condensing continuity because gpt40 is enabled.")
    return
  else:
    info("Condensing continuity because gpt40 is not enabled.")
  chat = [
    getContinuityPrompt(),
    getContinuity(),
    '''Please summarize and rewrite more concisely all of my book's Continuity Notes that you will need to remember while writing the rest of the book, in order to ensure continuity and consistency. Label this summary Continuity Notes.'''
  ]
  for i in range(2):
    continuity = getContinuity()
    if countTokens([continuity]) > 2000:
      action = "Condense Continuity"
      if i > 0:
        action = "Recondense Continuity"
      continuity = getChatAssistantResp(
        action,
        chat
      )
      setContinuity(continuity)

def getChatIntResp(action, msgs):
  for _ in range(6):
    respStr = re.sub(
      "[^0-9]",
      "", 
      getChatAssistantResp(action, msgs)
    )
    if respStr != "":
      return int(respStr)
  warn("***Unable to parse int from chat response.")
  return -1

def getChatAssistantResp(action, msgs):
  temp: float = settings["assistant"]["temp"]
  tokens = 0
  for msg in msgs:
    tokens += len(msg) / 4
  if tokens > 14000:
    if settings["gpt40Enabled"]:
      return getGpt40Resp(
        action, temp, msgs)
  return getGpt35Resp(action, temp, msgs)

def getChatAuthorResp(action, msgs):
  temp: float = settings["author"]["temp"]
  if not settings["gpt40Enabled"]:
    return getGpt35Resp(
      action, temp, msgs)
  return getGpt40Resp(action, temp, msgs)

def getGpt35Resp(
  action: str,
  temp: float,
  msgs: list[str]):
  try:
    return getSafeGptResp(
      action,
      chatModels["gpt35"],
      temp,
      getChatSystemRole(),
      msgs
    )
  except Exception as e:
    warn("***WARN: " + str(e))
    return ""
    
def getGpt40Resp(
  action: str,
  temp: float,
  msgs: list[str]):
  try:
    return getSafeGptResp(
      action,
      chatModels["gpt40"],
      temp,
      getChatSystemRole(),
      msgs
    )
  except Exception as e:
    warn("***WARN: " + str(e))
    return ""

def getSafeGptResp(
  action: str,
  model: str,
  temp: float,
  sysRole: str,
  msgs: list[str]):
  chatMsgs = [sysRole]
  for msg in msgs:
    role = "user"
    if (len(chatMsgs) % 2 == 0):
      role = "assistant"
    chatMsgs.append({
      "role": role,
      "content": msg})
  time.sleep(5)
  try:
    return getGptResp(
      action,
      model,
      temp,
      chatMsgs
    )
  except Exception as e:
    notice("Rsp Failed: " + str(e))
    time.sleep(15)
    try:
      return getGptResp(
        "Retry Failed " + action,
        model,
        temp,
        chatMsgs)
    except Exception as e:
      notice("Rsp Retry Failed: " + str(e))
      return "Failed Response Retry"
  
def getGptResp(
  action: str,
  model: str,
  temp: float,
  msgs: list[dict]):
  inputCost = model["pricing"]["input"]
  outputCost = model["pricing"]["output"]
  reqTokens = 0.0
  for msg in msgs:
    reqTokens += len(msg["content"]) / 5
  reqCost = reqTokens * inputCost
  bookCost = getBookCost() + reqCost
  book["cost"] = str(bookCost)
  notice(
    "${:.5f}; ".format(bookCost)
    + model["id"] + "; "
    + action
    + " Req Sent")
  reqStart = time.time()
  reqUrl = "https://api.openai.com/v1/chat/completions"
  reqAuth = "Bearer " + settings["apiKey"]
  reqHeaders = {
    "Content-Type": "application/json",
    "Authorization": reqAuth}
  reqParams = {
    "model": model["id"],
    "temperature": temp,
    "messages": msgs}
  postData= json.dumps(reqParams)
  response = simplePostBodyRequest(
    url=reqUrl,
    headers=reqHeaders,
    data=postData,
    timeout=settings["apiTimeout"])
#  response = requests.post(
#    url=reqUrl,
#    headers=reqHeaders,
#    data=postData,
#    timeout=settings["apiTimeout"]
#  ).json()
  respChoice = response["choices"][0]
  respMsg = respChoice["message"]
  respContent = respMsg["content"]
  usage = response["usage"]
  tokensIn = usage["prompt_tokens"]
  tokensOut = usage["completion_tokens"]
  reqEnd = time.time()
  tokensInCost = tokensIn * inputCost
  tokensOutCost = tokensOut * outputCost
  totalCost = tokensInCost+tokensOutCost
  respCost = totalCost - reqCost
  bookCost = getBookCost() + respCost
  book["cost"] = str(bookCost)
  duration = int(reqEnd - reqStart)
  if duration < 2:
    duration = 2
  notice(
    "${:.5f}; ".format(bookCost)
    + model["id"] + "; "
    + "Rsp Received In " 
    + str(duration) + " secs"
  )
  return respContent

def simplePostBodyRequest(
  url: str,
  headers: dict,
  data: str,
  timeout: int):
  httprequest = urllib.request.Request(
    url,
    data=data.encode(),
    method="POST",
    headers=headers)
  resp=urllib.request.urlopen(
    httprequest,
    timeout=timeout)
  respData=resp.read().decode()
  return json.loads(respData)
  
def countTokens(messages):
  tokens = 0
  for message in messages:
    tokens += len(message) / 4
  return tokens
  
def rewriteInFirstPerson(content):
  firstPersonPrompt = '''Rewrite the following content in first-person {protagionist}'s point of view. Use the following guidance:

Make sure that the total number of sentences in your rewrite at least matches the number of sentences in the original content's text.

Make sure that the total number of paragraphs in your rewrite at least matches the number of paragraphs in the original content's text.

Make sure to use a 'Show, dont tell' technique to show drama unfold on the page and place the main charater at the center of the story.

Make sure to use vivid and specific details to make descriptions more interesting and memorable. Avoid generic and clichéd descriptions. 

Make sure to be concise. Avoid long and drawn-out descriptions that slow down the pace of the story. Instead, choose specific details that are most important to the scene and use them to convey the desired mood or atmosphere.

Make sure to write in an engaging narrative style.

Make sure to write from a first-person perspective.

Make sure that the scene is rewritten to a {gradeLevel} grade reading level.

The content to rewrite:
```
{contentToRewrite}
```'''.format(
    contentToRewrite = content,
    protagionist = getProtagionist(),
    gradeLevel = getGradeLevelAsStr()
  )
  altFirstPersonPrompt = '''Rewrite the following scene in first-person from {protagionist}'s point of view.

Scene to rewrite:
```
{contentToRewrite}
```'''.format(
    contentToRewrite = content,
    protagionist = getProtagionist()
  )
  for i in range(6):
    resp = ""
    if i == 0:
      resp = getChatAssistantResp(
        "Rewrite In First-Person",
        [firstPersonPrompt]
      )
    elif i == 1:
      resp = getChatAssistantResp(
        "Rewrite In First-Person",
        [altFirstPersonPrompt]
      )
    elif i == 2:
      resp = getChatAuthorResp(
        "Rewrite In First-Person",
        [firstPersonPrompt]
      )
    else:
      resp = getChatAuthorResp(
        "Rewrite In First-Person",
        [altFirstPersonPrompt]
    )
    respContainsExclusion = False
    author = settings["author"]
    if "respExclusion" in author:
      for val in author["respExclusion"]:
        if val in resp:
          respContainsExclusion = True
    if respContainsExclusion:
      continue
    if len(resp) > float(len(content)) * .8:
      return resp
  warn("***WARN: Unable to convert content to first-person perspective.")
  return content

def p(line):
  return "\n" + line + "\n"

def debug(line):
  divider = "------------------------------"
  settings["logger"].debug(divider)
  settings["logger"].debug(line)

def info(line):
  divider = "------------------------------"
  settings["logger"].info(divider)
  settings["logger"].info(line)

def notice(line):
  divider = "------------------------------"
  settings["logger"].warning(divider)
  settings["logger"].warning(line)

def warn(line):
  divider = "------------------------------"
  settings["logger"].warning(divider)
  settings["logger"].warning(line)

def error(line):
  divider = "------------------------------"
  settings["logger"].error(divider)
  settings["logger"].error(line)

def critical(content):
  divider = "------------------------------"
  settings["logger"].warning(divider)
  settings["logger"].critical(content)

def getBookCost():
  if "cost" in book:
    return float(book["cost"])
  return 0.00
  
def getPerspective():
  if "perspective" in settings:
    return settings["perspective"]
  else:
    return "third-person"

def getGradeLevelAsInt():
  gradeLevel = 10
  if "gradeLevel" in settings:
    gradeLevel = int(settings["gradeLevel"])
  if gradeLevel > 0 and gradeLevel < 21:
    return gradeLevel
  return 10

def getGradeLevelAsStr():
  gradeLevel = getGradeLevelAsInt()
  if gradeLevel == 1:
    return "1st"
  if gradeLevel == 2:
    return "2nd"
  if gradeLevel == 3:
    return "3rd"
  if gradeLevel > 0 and gradeLevel < 21:
    return str(gradeLevel) + "th"
  return "10th"
  
def getTargetChapterLength():
  gradeLevel = getGradeLevelAsInt()
  return gradeLevel * 300
  
def getChatSystemRole():
  author = settings["author"]
  chatSystemRole = author["descr"]
  return {
    "role": "system",
    "content": chatSystemRole}
  
def getOutlinePrompt():
  return "Please print out my book's High-Level Outline. Include a list of characters and a short description of each character. Include a list of chapters and a short summary of what happens in each chapter."
    
def getOutline():
  return book["outline"]

def initOutline(outline):
  if "highLevelOutline" not in book:
    info("Setting initial book outline to:\n\n" + outline)
    book["outline"] = outline
  
def updateOutline(chNum):
  for i in range(4):
    chat = [
      getOutlinePrompt(),
      getOutline(),
      getProtagionistPrompt(),
      getProtagionist(),
      getContinuityPrompt(),
      getContinuity(),
      getCharDescsPrompt(),
      getCharDescs(),
      getChChronoPrompt(chNum),
      getChChrono(chNum),
      getChScenesPrompt(chNum),
      getChScenes(chNum),
      "Please edit and update my book's' high-level outline, taking into consideration my book's characters and notable items, Chronology, Continuity Notes, and draft of Chapter " + str(chNum) + ". Print out the updated high-level outline for my book. Include a list of characters and a short description of each character. Include a list of chapters and a short summary of what happens in each chapter."
    ]
    action = "Update Book Outline"
    if i > 0:
      action = "Retry " + action
    outline = getChatAssistantResp(
      action,
      chat
    )
    chat = [
      getOutlinePrompt(),
      outline,
      "Count and return as an integer the total number of chaters in my book's outline."
    ]
    chCount = getChatIntResp(
      "Count Chapters",
      chat
    )
    if chCount >= getChCount():
      setOutline(outline)
      debug(
        p("Setting chapter count to:") +
        p(str(chCount))
      )
      book["chCount"] = str(chCount)
      break

def setOutline(outline):
  debug("Setting book outline to:\n\n" + outline)
  book["outline"] = outline
  
def getCharDescsPrompt():
  return "Please print out a list of my book's characters, with short descriptions of them, and all settings in the story, with short descriptions. Also list any notable items or objects in the story, with short descriptions."
  
def getCharDescs():
  return book["charDescs"]
  
def setCharDescsInit(charDescs):
  info(p("Setting initial character descriptions to:") + p(charDescs))
  book["charDescs"] = charDescs
  
def setCharDescs(charDescs):
  debug(p("Setting character descriptions to:") + p(charDescs))
  book["charDescs"] = charDescs

def initProtagionist(charName):
  if "protagionist" not in book:
    debug("Setting protagionist to: " + charName)
    book["protagionist"] = charName

def getProtagionist():
  return book["protagionist"]

def getProtagionistPrompt():
  return '''Please print out my book's protagionist's name, who is also the main character of my book.'''

def updateContinuity(chNum):
  chContPrompt = '''Please briefly note any important details or facts from Chapter {chNum} that you need to remember while writing the rest of my book, in order to ensure continuity and consistency.'''.format(
    chNum=chNum
  )
  setChContinuity(
    chNum,
    getChatAssistantResp(
      "Update Chapter Continuity",
      [
        getOutlinePrompt(),
        getOutline(),
        getProtagionistPrompt(),
        getProtagionist(),
        getCharDescsPrompt(),
        getCharDescs(),
        getChChronoPrompt(chNum),
        getChChrono(chNum),
        getChDraftPrompt(chNum),
        getChDraft(chNum),
        chContPrompt
       ]
    )
  )
  continuity = ""
  if chNum > 5:
    condCont=""
    if "condCont" in book:
      condCont = book["condCont"],
    condContPrompt = '''Please summarize and rewrite more concisely my book's Continuity Notes that you will need to remember while writing the rest of the book, in order to ensure continuity and consistency.

Continuity Notes:
```
{condCont}
{newCont}
```'''.format(
      condCont=condCont,
      newCont=getChContinuity(
        chNum - 5)
    )
    condCont = getChatAssistantResp(
      "Condense Continuity",
      [condContPrompt]
    )
    debug("Setting Condensed Continuity Notes To:\n\n" + condCont)
    book["condCont"]=condCont
  rangeHigh = chNum + 1
  rangeLow = 1
  # GPT35 only has a 16k context window
  #   so a rolling continuity window is
  #   needed. GPT40 has a 128k context
  #   window so this becomes a non-issue
  if settings["gpt40Enabled"]:
    info("Do not use a rolling context window when condensing continuity notes because gpt40 is enabled.")
  else:
    info("Use a 4 chapter rolling context window when condensing continuity notes because gpt40 is not enabled.")
    if chNum > 5:
      rangeLow = chNum - 4
  for i in range(rangeLow, rangeHigh):
    continuity += "\n" + getChContinuity(i)
  setContinuity(continuity)
  return continuity

def updateCharDescs(chNum):
  chat = [
    getOutlinePrompt(),
    getOutline(),
    getProtagionistPrompt(),
    getProtagionist(),
    getContinuityPrompt(),
    getContinuity(),
    getCharDescsPrompt(),
    getCharDescs(),
    getChChronoPrompt(chNum),
    getChChrono(chNum),
    getChScenesPrompt(chNum),
    getChScenes(chNum),
    '''Please edit and update my book's lists of characters and notable items. Take into consideration my book's high-level outline, existing characters and notable items, Chronology, Continuity Notes, and draft of Chapter {chNum}. When listimg out characters please include a short descriptions of them. Also include a short description for each of the listed notable items.'''.format(
      chNum = chNum
    )
  ]
  charDescs = getChatAssistantResp(
    "Update Char Descrs",
    chat
  )
  setCharDescs(charDescs)
  return charDescs

def initTitle():
  chat = [
    getOutlinePrompt(),
    getOutline(),
    '''Please suggest a good title for my book taking into consideration my book's High-Level Outline. Make sure to respond with only the title.'''
  ]
  action = "Init Title"
  title = getChatAuthorResp(action, chat)
  if "title:" in title.lower():
    title = title[title.find("title:") + 6].trim()
  info(p("Setting initial title to:"))
  critical(title)
  book["title"] = title
  
def getContinuityPrompt():
  return '''Please briefly note any important details or facts from this book's from Continuity Notes that you need to remember while writing the rest of the book, in order to ensure continuity and consistency. Label these Continuity Notes.'''

def getContinuity():
  return book["continuity"]
  
def setContinuity(continuity):
  debug("Setting continuity notes to:\n\n" + continuity)
  book["continuity"] = continuity

def updateChCount():
  chCount = getChatIntResp(
    "Count Chapters",
    [
      getOutlinePrompt(),
      getOutline(),
      '''Count and return as an integer the total number of chapters in my book's outline.'''
    ]
  )
  if chCount > 0:
    debug(
      p("Setting chapter count to:") +
      p(str(chCount))
    )
    book["chCount"] = str(chCount)
  
def getChCount():
  return int(book["chCount"])
    
def isLastCh(chNum):
  return chNum >= getChCount()
  
def getChScenesPrompt(chNum):
  return "Please print out my book's draft of Chapter " + str(chNum) + " that has all already happened and should not be repeated."

def getChScenes(chNum):
  chapter = getChapter(chNum)
  scenes = chapter["scenes"]
  return """

* * *

""".join(scenes)

def getChapter(chNum):
  chKey = "ch" + str(chNum)
  return book["chapters"][chKey]

def saveChapter(chNum, scenes):
  if "chapters" not in book:
    book["chapters"] = {}
  chapters = book["chapters"]
  chapter = {}
  chapters["ch" + str(chNum)] = chapter
  chapter["scenes"] = scenes
  chapter["bookCost"] = book["cost"]
  chapter["bookTitle"] = book["title"]
  #updateOutline(chNum)
  outline = getOutline()
  chapter["bookOutline"] = outline
  chapter["bookChCount"] = getChCount()
  chapter["isBookDone"]=isLastCh(chNum)
  protagionist = getProtagionist()
  chapter["bookProtagionist"] =protagionist
  charDescs = updateCharDescs(chNum)
  chapter["bookCharDescs"] = charDescs
  continuity = updateContinuity(chNum)
  chapter["bookContinuity"] = continuity
  debug("""Saving Chapter {chNum} as:

{chObj}""".format(
    chNum = chNum,
    chObj = chapter))

def loadSaveState(chNum, save):
  book.clear()
  for key in save:
    book[key] = save[key]
  prevCh = getChapter(chNum - 1)
  book["cost"] = prevCh["bookCost"]
  book["title"] = prevCh["bookTitle"]
  book["outline"] = prevCh["bookOutline"]
  chCount = prevCh["bookChCount"]
  book["chCount"] = chCount
  protagionist = prevCh["bookProtagionist"]
  book["protagionist"] = protagionist
  charDescs = prevCh["bookCharDescs"]
  book["charDescs"] = charDescs
  continuity = prevCh["bookContinuity"]
  book["continuity"] = continuity
  book["theEnd"] = prevCh["isBookDone"]

def loadSettings(
  apiKey: str,
  gpt40Enabled: bool,
  firstPerson: bool,
  author: dict,
  gradeLevel: int,
  logger: logging.Logger):
  settings["logger"] = logger
  settings["apiKey"] = apiKey
  settings["apiTimeout"] = 300
  settings["author"] = author.copy()
  assistant = helpfulAssistant.copy()
  settings["assistant"] = assistant
  if gpt40Enabled:
    notice("Chat GPT-4 is enabled.")
  else:
    notice("Chat GPT-4 is disabled.")
  settings["gpt40Enabled"] = gpt40Enabled
  perspective = "third-person"
  if firstPerson:
    perspective = "first-person"
  notice(
    "Setting perspective to: " + perspective)
  settings["perspective"] = perspective
  notice(
    "Setting reading level to: grade " 
    + str(gradeLevel))
  settings["gradeLevel"] = str(gradeLevel)

def getChContinuityPrompt(chNum):
  return "Please briefly note any important details or facts from this book's Continuity Notes that you will need to remember while writing Chapter " + str(chNum) + " of my book, in order to ensure continuity and consistency. Label these Continuity Notes."
  
def setChContinuity(chNum, notes):
  debug(p("Setting chapter" + str(chNum) + " continuity notes to:") + p(notes))
  book["ch" + str(chNum) + "Continuity"] = notes
  
def getChContinuity(chNum):
  return book["ch" + str(chNum) + "Continuity"]
     
def getChCharDescPromptMsg(chNum):
  return {"role": "user", "content": getChCharDescsPrompt(chNum)}
  
def getChCharDescMsg(chNum):
  return {"role": "user", "content": getChCharDescs(chNum)}
        
def getChCharDescsPrompt(chNum):
  return "Please print out a list of my book's relevant characters, with short descriptions, that you will need to know about to write Chapter " + str(chNum) + " of my book taking into consideration my book's high-level outline, characters and notable items, previou Chronological events, and Continuity Notes. Also list any notable items or objects in the story, with short descriptions, that you will need to know about to write Chapter " + str(chNum) + " of my book."
  
def setChCharDescs(chNum, descs):
  debug(p("Setting chapter" + str(chNum) + " character descriptions to:") + p(descs))
  book["ch" + str(chNum) + "CharDescs"] = descs
  
def getChCharDescs(chNum):
  return book["ch" + str(chNum) + "CharDescs"]

def updateChChrono(chNum):
  chronoPrompt = "Please print out the relevant chronological events that you will need to know about to write Chapter " + str(chNum) + " of my book taking into consideration my book's high-level outline. The relevant chronological events for Chapter " + str(chNum) + " should describe when the characters pass from one setting to another setting, when characters first meet each other, and anything else needed to ensure continuity and consistency during the writing process."
  chat = [
    getOutlinePrompt(),
    getOutline(),
    getProtagionistPrompt(),
    getProtagionist(),
    chronoPrompt
  ]
  setChChrono(
    chNum,
    getChatAssistantResp(
      '''Update Ch {chNum} Chrono'''.format(
        chNum = chNum
      ),
      chat
    )
  )

def getChChronoPrompt(chNum):
  return "Please print out the relevant chronological events that you will need to know about to write Chapter " + str(chNum) + " of my book."

def setChChrono(chNum, chrono):
  debug(p("Setting chapter" + str(chNum) + " chrono to:") + p(chrono))
  book["ch" + str(chNum) + "Chrono"] = chrono
  
def getChChrono(chNum):
  return book["ch" + str(chNum) + "Chrono"]

def getChOpeningScenePrompt(chNum):
  return "Please print out my book's opening scene for Chapter " + str(chNum)
  
def setChOpeningScene(chNum, scene):
  debug(p("Setting chapter " + str(chNum) + " opening scene to:") + p(scene))
  book["ch" + str(chNum) + "OpeningScene"] = scene
  
def getChOpeningScene(chNum):
  chOpeningSceneKey = "ch" + str(chNum) + "OpeningScene"
  if chOpeningSceneKey in book:
    return book[chOpeningSceneKey]
  else:
    return "Please reference my book's High-Level Outline and Chronology to infer what the Opening Scene of Chapter " + str(chNum) + " should be."
  
def getChFinalScenePrompt(chNum):
  return "Please print out my book's final scene for Chapter " + str(chNum)
  
def setChFinalScene(chNum, scene):
  debug(p("Setting chapter " + str(chNum) + " final scene to:") + p(scene))
  book["ch" + str(chNum) + "FinalScene"] = scene
  
def getChFinalScene(chNum):
  chOpeningSceneKey = "ch" + str(chNum) + "FinalScene"
  if chOpeningSceneKey in book:
    return book[chOpeningSceneKey]
  else:
    return "Please reference my book's High-Level Outline and Chronology to infer what the Final Scene of Chapter " + str(chNum) + " should be."

def getChOutlinePrompt(chNum):
  return "Please print out the chapter outline for my book's draft of Chapter " + str(chNum)

def setChOutline(chNum, outline):
  debug("Setting outline of Chapter " + str(chNum) + " to:\n\n" + outline)
  book["ch" + str(chNum) + "Outline"] = outline

def getChOutline(chNum):
  return book["ch" + str(chNum) + "Outline"]

def getChDraftPrompt(chNum):
  return "Please print out my book's draft of Chapter " + str(chNum)

def setChDraft(chNum, draft):
  debug("Setting draft of Chapter " + str(chNum) + " to:\n\n" + draft)
  book["ch" + str(chNum) + "Draft"] = draft

def getChDraft(chNum):
  return book["ch" + str(chNum) + "Draft"]

def getScenePrompt(chNum, sceneNum):
  return "For my book, please print out Scene " + str(sceneNum) + " of Chapter " + str(chNum) + ". The events of this scene have already happened, will not change, and must not be repeated."
