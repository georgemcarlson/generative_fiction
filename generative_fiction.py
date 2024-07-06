import re
import time
from openai import OpenAI
import logging

# https://medium.com/@chiaracoetzee/generating-a-full-length-work-of-fiction-with-gpt-4-4052cfeddef3

book = {}
settings =  {}

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

helpfulAssistant = {
  "temp": .8,
  "descr": "You are a helpful assistant."
}

def writeBook(args):
  theBook = {}
  theBook["theEnd"] = False
  theBook["chapters"] = {}
  # using a while loop because the total
  #   number of chapters can change over
  #   time.
  while not theBook["theEnd"]:
    chNum = len(theBook["chapters"]) + 1
    theBook = writeChapter(
      chNum,
      theBook,
      args)

def writeChapter(chNum, save, args):
  loadSettings(args)
  gradeLevel = getGradeLevelAsInt()
  book["continuity"] = ""
  book["theEnd"] = False
  if chNum == 0:
    return book.copy()
  elif chNum == 1:
    initOutlinePrompt = args["prompt"]
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
  chDraft = getChatAuthorResp(
    '''Ch {thisChNum} 1st Draft'''.format(
      thisChNum = chNum
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
      '''Write a final draft of Chapter {thisChNum}. Use the following guidance:

Begin the final draft with the beginning of the first scene of Chapter {thisChNum}. Only include the contents of the scenes in the final draft of Chapter {thisChNum}. Seperate each scene with '\n\n***\n\n'. Finish the final draft immediately after the ending of the last scene of Chapter {thisChNum}.

The final draft of Chapter {thisChNum} should set up the story for Chapter {nextChNum}, which will come immediately afterwards.

Make sure that the chapter contains between {wordRangeLow} and {wordRangeHigh} words.

Make sure to use a 'Show, dont tell' technique to show drama unfold on the page and place {theProtagionist}, the main charater, at the center of the story.

Make sure to use vivid and specific details to make descriptions more interesting and memorable. Avoid generic and clichéd descriptions. 

Make sure to be concise. Avoid long and drawn-out descriptions that slow down the pace of the story. Instead, choose specific details that are most important to the scene and use them to convey the desired mood or atmosphere.

Make sure to write in an engaging narrative style.

Make sure that the chapter is rewritten to a {thisGradeLevel} grade reading level.'''.format(
        wordRangeLow = 250 * gradeLevel,
        wordRangeHigh = 350 * gradeLevel,
        theProtagionist = getProtagionist(),
        thisChNum = chNum,
        nextChNum = chNum + 1,
        thisGradeLevel = gradeLevel
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
{thisScene}
```'''.format(
        thisScene = sceneDraft)
      ])
    chOutline += '''

Scene {thisSceneNum}:
{thisSceneOutline}'''.format(
      thisSceneNum=i+1,
      thisSceneOutline=sceneOutline.strip()
    )
  setChOutline(chNum, chOutline.strip())
  chDraft = getChatAuthorResp(
    '''Ch {thisChNum} 2nd Draft'''.format(
      thisChNum = chNum
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
      '''Write a final draft of Chapter {thisChNum}. Use the following guidance:

Begin the final draft with the beginning of the first scene of Chapter {thisChNum}. Only include the contents of the scenes in the final draft of Chapter {thisChNum}. Seperate each scene with '\n\n***\n\n'. Finish the final draft immediately after the ending of the last scene of Chapter {thisChNum}.

The final draft of Chapter {thisChNum} should set up the story for Chapter {nextChNum}, which will come immediately afterwards.

Make sure that the chapter contains between {wordRangeLow} and {wordRangeHigh} words.

Make sure to use a 'Show, dont tell' technique to show drama unfold on the page and place the main charater at the center of the story.

Make sure to use vivid and specific details to make descriptions more interesting and memorable. Avoid generic and clichéd descriptions. 

Make sure to be concise. Avoid long and drawn-out descriptions that slow down the pace of the story. Instead, choose specific details that are most important to the scene and use them to convey the desired mood or atmosphere.

Make sure to write in an engaging narrative style.

Make sure that the chapter is rewritten to a {thisGradeLevel} grade reading level.'''.format(
        wordRangeLow = 250 * gradeLevel,
        wordRangeHigh = 350 * gradeLevel,
        thisChNum = chNum,
        nextChNum = chNum + 1,
        thisGradeLevel = gradeLevel
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
    '''Count Ch {thisChNum} Scenes'''.format(
      thisChNum = chNum
    ),
    [
      '''Count and return as an integer the total number of scenes in the following chapter:

```
{thisChDraft}
```'''.format(
        thisChDraft="***".join(chDraftScenes)
      )
    ]
  )
  if sceneCount < 2:
    sceneCount = len(chDraftScenes)
  elif sceneCount > len(chDraftScenes):
    sceneCount = len(chDraftScenes)
  info('''Ch {thisChNum} scene count: {thisSceneCount}'''.format(
    thisChNum = chNum,
    thisSceneCount = sceneCount
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
    '''Scene {thisSceneNum}: First Para'''.format(thisSceneNum=sceneNum),
    [
      '''Return only the first opening paragraph of the following scene:

```
{thisScene}
```'''.format(
    thisScene = sceneDraft)
  ])
  info("First Opening paragraph:\n\n"+firstParagraph)
  lastParagraph = getChatAssistantResp(
    '''Scene {thisSceneNum}: Last Para'''.format(thisSceneNum=sceneNum),
    [
      '''Return only the last final paragraph of the following scene:"

```
{thisScene}
```'''.format(
    thisScene = sceneDraft)
  ])
  info("Last Final paragraph:\n\n" + lastParagraph)
  qualityControlPrompt = '''Please rewrite Scene {thisSceneNum} for Chapter {thisChNum} of my book to be a longer more detailed version. Use the following guidance:

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
    thisSceneNum=sceneNum,
    thisChNum=chNum,
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
        '''Please write Scene {thisSceneNum} for Chapter {thisChNum} of my book.'''.format(
          thisSceneNum=sceneNum,
          thisChNum=chNum
        ),
        sceneDraft,
        '''Return the first paragraph from Chapter {thisChNum} Scene {thisSceneNum} of my book.'''.format(
          thisSceneNum=sceneNum,
          thisChNum=chNum
        ),
        firstParagraph,
        '''Return the last paragraph from Chapter {thisChNum} Scene {thisSceneNum} of my book.'''.format(
          thisSceneNum=sceneNum,
          thisChNum=chNum
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
  sceneContinuityNotesPrompt = '''Please briefly note any important details or facts from Scene {thisSceneNum} that you need to remember while writing the rest of Chapter {thisChNum} of my book, in order to ensure continuity and consistency throughout the chapter. Begin the continuity notes with the first continuity note from Scene {thisSceneNum}. Only include the continuity notes for Scene {thisSceneNum} in your response.

Continuity Notes:'''.format(
    thisChNum=chNum,
    thisSceneNum=sceneNum
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

Scene {thisSceneNum} Continuity Notes:

{thisSceneContinuity}
  '''.format(
    chContinuity = getChContinuity(chNum),
    thisSceneNum = sceneNum,
    thisSceneContinuity = sceneContinuity
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
      '''Ch {thisChNum} Continuity'''.format(
        thisChNum = chNum
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
      '''Ch {thisChNum} Char Descs'''.format(
        thisChNum = chNum
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
    '''For Chapter {thisChNum} of my book, write a detailed chapter outline taking into consideration my book's high-level outline, relevant characters and notable items, Chronology, Continuity Notes, and the Opening and Final scenes for Chapter {thisChNum}. The chapter outline must list all the scenes in the chapter and a short description of each. Begin the chapter outline with the Opening Scene from Chapter {thisChNum}, and finish the outline with the Final Scene from Chapter {thisChNum}.'''.format(
      thisChNum = chNum
    )
  ]
  setChOutline(
    chNum,
    getChatAssistantResp(
      '''Ch {thisChNum} Outline'''.format(
        thisChNum = chNum
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
    action = '''Ch {thisChNum} Opening Scene'''.format(
      thisChNum = chNum
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
    action = '''Ch {thisChNum} Final Scene'''.format(
      thisChNum = chNum
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
  temp = settings["assistant"]["temp"]
  tokens = 0
  for msg in msgs:
    tokens += len(msg) / 4
  if tokens > 14000:
    if settings["gpt40Enabled"]:
      return getGpt40Resp(
        action, temp, msgs)
  return getGpt35Resp(action, temp, msgs)

def getChatAuthorResp(action, msgs):
  temp = settings["author"]["temp"]
  if not settings["gpt40Enabled"]:
    return getGpt35Resp(
      action, temp, msgs)
  return getGpt40Resp(action, temp, msgs)

def getGpt35Resp(action, temp, msgs):
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
    
def getGpt40Resp(action, temp, msgs):
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
  action,
  model,
  temp,
  sysRole,
  msgs):
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
  except:
    notice("Rsp Failed")
    time.sleep(15)
    try:
      return getGptResp(
        "Retry Failed " + action,
        model,
        temp,
        chatMsgs)
    except:
      notice("Rsp Retry Failed")
      return "Failed Response Retry"
  
def getGptResp(
  action,
  model,
  temp,
  msgs):
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
  client = OpenAI(
    api_key = settings["apiKey"],
    timeout = settings["apiTimeout"],
    max_retries = 2
  )
  response = client.chat.completions.create(
      model=model["id"],
      messages=msgs,
      temperature=temp)
  respMsg = response.choices[0].message
  respContent = respMsg.content
  usage = response.usage
  tokensIn = usage.prompt_tokens
  tokensOut = usage.completion_tokens
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
  
def countTokens(messages):
  tokens = 0
  for message in messages:
    tokens += len(message) / 4
  return tokens
  
def rewriteInFirstPerson(content):
  firstPersonPrompt = '''Rewrite the following content in first-person {theProtagionist}'s point of view. Use the following guidance:

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
    theProtagionist = getProtagionist(),
    gradeLevel = getGradeLevelAsStr()
  )
  altFirstPersonPrompt = '''Rewrite the following scene in first-person from {theProtagionist}'s point of view.

Scene to rewrite:
```
{contentToRewrite}
```'''.format(
    contentToRewrite = content,
    theProtagionist = getProtagionist()
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
    '''Please edit and update my book's lists of characters and notable items. Take into consideration my book's high-level outline, existing characters and notable items, Chronology, Continuity Notes, and draft of Chapter {thisChNum}. When listimg out characters please include a short descriptions of them. Also include a short description for each of the listed notable items.'''.format(
      thisChNum = chNum
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
  debug("""Saving Chapter {thisChNum} as:

{thisChObj}""".format(
    thisChNum = chNum,
    thisChObj = chapter))

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

def loadSettings(args):
  logger = logging.getLogger("default")
  if "logger" in args:
    logger = args["logger"]
  settings["logger"] = logger
  settings["apiKey"] = args["apiKey"]
  settings["apiTimeout"] = 300
  author = args["author"]
  settings["author"] = author
  settings["assistant"] = helpfulAssistant
  gpt40Enabled = True
  if "gpt40Enabled" in args:
    gpt40Enabled = args["gpt40Enabled"]
  if gpt40Enabled:
    notice("Chat GPT-4 is enabled.")
  else:
    notice("Chat GPT-4 is disabled.")
  settings["gpt40Enabled"] = gpt40Enabled
  perspective = "third-person"
  if "firstPerson" in args:
    if args["firstPerson"]:
      perspective = "first-person"
  notice(
    "Setting perspective to: " + perspective)
  settings["perspective"] = perspective
  if "gradeLevel" in args:
    gradeLevel = args["gradeLevel"]
    notice(
      "Setting reading level to: grade " 
      + str(gradeLevel)
    )
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
      '''Update Ch {thisChNum} Chrono'''.format(
        thisChNum = chNum
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
