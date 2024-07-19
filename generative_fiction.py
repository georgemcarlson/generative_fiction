import re
import time
import logging
import json
import urllib.request

# https://medium.com/@chiaracoetzee/generating-a-full-length-work-of-fiction-with-gpt-4-4052cfeddef3

chatModels = {
  "small": {
    "id": "gpt-4o-mini",
    "pricing": {
      "input": (0.15 / 1000000),
      "output": (0.6 / 1000000)
    }
  },
  "large": {
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

def p(line):
  return "\n" + line + "\n"

class GenerativeFiction:
  
  book: dict = {}
  
  # settings
  apiKey: str
  apiTimeout: int = 300
  largeModelEnabled: bool
  firstPersonEnabled: bool
  author: dict
  assistant: dict = helpfulAssistant.copy()
  prompt: str
  gradeLevel: int
  logger: logging.Logger
  
  # class constructor
  def __init__(
    self,
    apiKey: str = None,
    largeModel: bool = True,
    authorDescr: str = defAuthor["descr"],
    authorTemp: float = defAuthor["temp"],
    authorRespExclusions: list[str] = None,
    prompt: str = None,
    gradeLevel: int = 10,
    logger: logging.Logger = defLogger):
    self.apiKey=apiKey
    self.largeModelEnabled = largeModel
    author = {
      "descr": authorDescr,
      "temp": authorTemp}
    if authorRespExclusions is not None:
      exclusions = authorRespExclusions
      author["respExclusion"] = exclusions
    self.author = author.copy()
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
    lgChatModelId=chatModels["large"]["id"]
    if self.largeModelEnabled:
      self.notice(lgChatModelId+" enabled")
    else:
      self.notice(lgChatModelId+" disabled")
    if firstPerson:
      self.notice(
        "Setting perspective to: first-person")
    else:
      self.notice(
        "Setting perspective to: third-person")
    self.notice(
      "Setting reading level to: grade " 
      + str(self.gradeLevel))
    self.firstPersonEnabled = firstPerson
    self.book.clear()
    self.book["continuity"] = ""
    self.book["theEnd"] = False
    self.book["chapters"] = {}
    if chNum == 0:
      return self.book.copy()
    elif chNum == 1:
      initOutlinePrompt = self.prompt
      self.initLvl1Notes(initOutlinePrompt)
    else:
      self.debug("Loading Save State...")
      self.loadSaveState(chNum, save)
    if self.book["theEnd"]:
      self.critical(p(p(p("The End"))))
      return self.book.copy()
    self.info("Writing next chapter:")
    self.critical(
      p(p(p("Chapter: " + str(chNum)))))
    if self.isLastCh(chNum):
      self.outlineFinalChapter()
    else:
      self.outlineChapter(chNum)
    wordRangeLow = 250 * self.gradeLevel,
    wordRangeHigh = 350 * self.gradeLevel,
    chDraft = self.chatAuthorResp(
      '''Ch {chNum} 1st Draft'''.format(
        chNum = chNum
      ),
      [
        self.getOutlinePrompt(),
        self.getOutline(),
        self.getProtagionistPrompt(),
        self.getProtagionist(),
        self.getChCharDescsPrompt(chNum),
        self.getChCharDescs(chNum),
        self.getChChronoPrompt(chNum),
        self.getChChrono(chNum),
        self.getChOutlinePrompt(chNum),
        self.getChOutline(chNum),
        self.getChContinuityPrompt(chNum),
        self.getChContinuity(chNum),
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
          protagionist = self.getProtagionist(),
          chNum = chNum,
          nextChNum = chNum + 1,
          gradeLevel = self.gradeLevel
        )
      ]
    )
    self.info("Ch Draft:\n\n" + chDraft)
    chDraftScenes = self.parseScenes(chDraft)
    sceneCount = self.countScenes(
      chNum,
      chDraftScenes)
    chOutline = ""
    for i in range(int(sceneCount)):
      sceneDraft = chDraftScenes[i].strip()
      sceneOutline=self.chatAssistantResp(
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
    self.setChOutline(
      chNum,
      chOutline.strip())
    wordRangeLow = 250 * self.gradeLevel
    wordRangeHigh = 350 * self.gradeLevel
    chDraft = self.chatAuthorResp(
      '''Ch {chNum} 2nd Draft'''.format(
        chNum = chNum
      ),
      [
        self.getOutlinePrompt(),
        self.getOutline(),
        self.getProtagionistPrompt(),
        self.getProtagionist(),
        self.getChCharDescsPrompt(chNum),
        self.getChCharDescs(chNum),
        self.getChChronoPrompt(chNum),
        self.getChChrono(chNum),
        self.getChOutlinePrompt(chNum),
        self.getChOutline(chNum),
        self.getChContinuityPrompt(chNum),
        self.getChContinuity(chNum),
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
    self.setChDraft(chNum, chDraft)
    chDraftScenes = self.parseScenes(chDraft)
    sceneCount = self.countScenes(
      chNum,
      chDraftScenes)
    scenes = []
    for i in range(int(sceneCount)):
      scene = self.writeScene(
        chNum,
        i+1,
        chDraftScenes)
      scenes.append(scene)
      if i > 1:
        self.critical(p("* * *"))
      self.critical(p(scene))
    self.saveChapter(chNum, scenes)
    return self.book.copy()

  def parseScenes(
    self,
    chDraft: str):
    cleanScenes = []
    for scene in chDraft.split("***"):
      if len(scene) < 100:
        continue
      if "." not in scene:
        continue
      if scene.strip().startswith("Chapter"):
        continue
      cleanScenes.append(scene.strip())
    return cleanScenes

  def countScenes(
    self,
    chNum: int,
    scenes: list[str]):
    sceneCount = self.getChatIntResp(
      '''Count Ch {chNum} Scenes'''.format(
        chNum = chNum
      ),
      [
        '''Count and return as an integer the total number of scenes in the following chapter:
  
  ```
  {chDraft}
  ```'''.format(
          chDraft=p(p("***")).join(scenes)
        )
      ]
    )
    if sceneCount < 2:
      sceneCount = len(scenes)
    elif sceneCount > len(scenes):
      sceneCount = len(scenes)
    self.info('''Ch {chNum} scene count: {sceneCount}'''.format(
      chNum = chNum,
      sceneCount = sceneCount))
    return sceneCount
  
  def rewriteScene(
    self,
    chNum: int,
    sceneNum: int,
    chDraftScenes: list[str]):
    sceneCount = len(chDraftScenes)
    chLen = self.getTargetChapterLength()
    sceneLen= chLen / sceneCount
    sceneDraft = chDraftScenes[sceneNum - 1].strip()
    if self.getGradeLevelAsInt() < 4:
      return sceneDraft
    firstParagraph=self.chatAssistantResp(
      '''Scene {sceneNum}: First Para'''.format(sceneNum=sceneNum),
      [
        '''Return only the first opening paragraph of the following scene:
  
  ```
  {sceneDraft}
  ```'''.format(
      sceneDraft = sceneDraft)
    ])
    self.info("First Opening paragraph:\n\n"+firstParagraph)
    lastParagraph=self.chatAssistantResp(
      '''Scene {sceneNum}: Last Para'''.format(sceneNum=sceneNum),
      [
        '''Return only the last final paragraph of the following scene:"
  
  ```
  {sceneDraft}
  ```'''.format(
      sceneDraft = sceneDraft)
    ])
    self.info("Last Final paragraph:\n\n" + lastParagraph)
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
      gradeLevel=self.getGradeLevelAsStr())
    for _ in range(4):
      scene = self.chatAuthorResp(
        "Rewrite Scene " + str(sceneNum),
        [
          self.getChCharDescsPrompt(chNum),
          self.getChCharDescs(chNum),
          self.getChChronoPrompt(chNum),
          self.getChChrono(chNum),
          self.getChOutlinePrompt(chNum),
          self.getChOutline(chNum),
          self.getChContinuityPrompt(chNum),
          self.getChContinuity(chNum),
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
      self.debug("QC Scene:\n\n" + scene)
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
    self,
    chNum: int,
    sceneNum: int,
    chDraftScenes: list[str]):
    scene = self.rewriteScene(
      chNum,
      sceneNum,
      chDraftScenes)
    sceneContinuityNotesPrompt = '''Please briefly note any important details or facts from Scene {sceneNum} that you need to remember while writing the rest of Chapter {chNum} of my book, in order to ensure continuity and consistency throughout the chapter. Begin the continuity notes with the first continuity note from Scene {sceneNum}. Only include the continuity notes for Scene {sceneNum} in your response.
  
  Continuity Notes:'''.format(
      chNum=chNum,
      sceneNum=sceneNum)
    sceneContinuity=self.chatAssistantResp(
      "Scene Continuity Notes",
      [
        self.getOutlinePrompt(),
        self.getOutline(),
        self.getProtagionistPrompt(),
        self.getProtagionist(),
        self.getChCharDescsPrompt(chNum),
        self.getChCharDescs(chNum),
        self.getChChronoPrompt(chNum),
        self.getChChrono(chNum),
        self.getChDraftPrompt(chNum),
        self.getChDraft(chNum),
        self.getContinuityPrompt(),
        self.getContinuity(),
        self.getScenePrompt(
          chNum, sceneNum),
        scene,
        sceneContinuityNotesPrompt
      ]
    )
    updatedChContinuity = '''{chContinuity}
  
  Scene {sceneNum} Continuity Notes:
  
  {sceneContinuity}
    '''.format(
      chContinuity = self.getChContinuity(chNum),
      sceneNum = sceneNum,
      sceneContinuity = sceneContinuity)
    self.setChContinuity(
      chNum,
      updatedChContinuity)
    if self.getPerspective() == "first-person":
      scene=self.rewriteIn1stPerson(scene)
    return scene
    
  def outlineFinalChapter(self):
    chNum = self.getChCount()
    self.updateChChrono(chNum)
    finalChContinuityPrompt = '''Please briefly note any important details or facts from this book's Continuity Notes that you will need to remember while writing the Final Chapter of my book, in order to ensure continuity and consistency. Label these Continuity Notes. Make sure to remember that the Final Chapter of my book will conclude my book.'''
    finalChCharDescsPrompt = '''Please print out a list of my book's relevant characters, with short descriptions, that you will need to know about to write the Final Chapter of my book taking into consideration my book's high-level outline, characters and notable items, Chronology, Continuity Notes. Also list any notable items or objects in the story, with short descriptions, that you will need to know about to write the Final Chapter of my book. Make sure to remember that the Final Chapter of my book will conclude my book.'''
    finalChOpeningScenePrompt = '''For the Final Chapter of my book, please write a detailed outline describing the first, opening scene taking into consideration my book's high-level outline, relevant characters and notable items, Chronology, and Continuity Notes. It should describe what happens in that opening scene and set up the story for the rest of the book. Do not summarize the entire chapter, only the first scene. The opening scene of the Final Chapter should directly follow the final scene of Chapter {prevChNum}'''.format(prevChNum = chNum -1)
    finalChFinalScenePrompt = '''For the Final Chapter of my book, write a detailed outline describing the final, last scene of the chapter taking into consideration my book's high-level outline, relevant characters and notable items, Chronology, and Continuity Notes. It should describe what happens at the very end of the chapter, and conclude the book.'''
    finalChOutlinePrompt = '''For the Final Chapter of my book, write a detailed chapter outline taking into consideration my book's high-level outline, relevant characters and notable items, Chronology, Continuity Notes, and the Opening and Final scenes for the Final Chapter. The chapter outline must list all the scenes in the chapter and a short description of each. Begin the chapter outline with the Opening Scene from the Final Chapter, and finish the outline with the Final Scene from the Final Chapter. This chapter outline must conclude the book.'''
    chat = [
      self.getOutlinePrompt(),
      self.getOutline(),
      self.getProtagionistPrompt(),
      self.getProtagionist(),
      self.getCharDescsPrompt(),
      self.getCharDescs(),
      self.getChChronoPrompt(chNum),
      self.getChChrono(chNum),
      self.getContinuityPrompt(),
      self.getContinuity(),
      finalChContinuityPrompt
    ]
    self.setChContinuity(
      chNum,
      self.chatAssistantResp(
        "Final Ch Continuity",
        chat))
    chat.extend([
      self.getChContinuity(chNum),
      finalChCharDescsPrompt])
    self.setChCharDescs(
      chNum,
      self.chatAssistantResp(
        "Final Ch Char Descrs",
        chat))
    chOpenScene = self.chatAssistantResp(
      "Final Ch Opening Scene",
      [
        self.getOutlinePrompt(),
        self.getOutline(),
        self.getProtagionistPrompt(),
        self.getProtagionist(),
        finalChCharDescsPrompt,
        self.getChCharDescs(chNum),
        self.getChChronoPrompt(chNum),
        self.getChChrono(chNum),
        finalChContinuityPrompt,
        self.getChContinuity(chNum),
        finalChOpeningScenePrompt
      ]
    )
    chFinalScene = self.chatAssistantResp(
      "Final Ch Final Scene",
      [
        self.getOutlinePrompt(),
        self.getOutline(),
        self.getProtagionistPrompt(),
        self.getProtagionist(),
        finalChCharDescsPrompt,
        self.getChCharDescs(chNum),
        self.getChChronoPrompt(chNum),
        self.getChChrono(chNum),
        finalChContinuityPrompt,
        self.getChContinuity(chNum),
        finalChOpeningScenePrompt,
        chOpenScene,
        finalChFinalScenePrompt
      ]
    )
    self.setChOutline(
      chNum,
      self.chatAssistantResp(
        "Final Ch Outline",
        [
          self.getOutlinePrompt(),
          self.getOutline(),
          self.getProtagionistPrompt(),
          self.getProtagionist(),
          finalChCharDescsPrompt,
          self.getChCharDescs(chNum),
          self.getChChronoPrompt(chNum),
          self.getChChrono(chNum),
          finalChContinuityPrompt,
          self.getChContinuity(chNum),
          finalChOpeningScenePrompt,
          chOpenScene,
          finalChFinalScenePrompt,
          chFinalScene,
          finalChOutlinePrompt
        ]
      )
    )
    
  def outlineChapter(
    self,
    chNum: int):
    self.updateChChrono(chNum)
    self.setBoundingScenes(chNum)
    chat = [
      self.getOutlinePrompt(),
      self.getOutline(),
      self.getProtagionistPrompt(),
      self.getProtagionist(),
      self.getContinuityPrompt(),
      self.getContinuity(),
      self.getCharDescsPrompt(),
      self.getCharDescs(),
      self.getChChronoPrompt(chNum),
      self.getChChrono(chNum),
      self.getChContinuityPrompt(chNum)
    ]
    self.setChContinuity(
      chNum,
      self.chatAssistantResp(
        '''Ch {chNum} Continuity'''.format(
          chNum = chNum
        ),
        chat
      )
    )
    chat.extend([
      self.getChContinuity(chNum),
      self.getChCharDescsPrompt(chNum)
    ])
    self.setChCharDescs(
      chNum,
      self.chatAssistantResp(
        '''Ch {chNum} Char Descs'''.format(
          chNum = chNum
        ),
        chat
      )
    )
    chat = [
      self.getOutlinePrompt(),
      self.getOutline(),
      self.getProtagionistPrompt(),
      self.getProtagionist(),
      self.getChCharDescsPrompt(chNum),
      self.getChCharDescs(chNum),
      self.getChChronoPrompt(chNum),
      self.getChChrono(chNum),
      self.getChOpeningScenePrompt(chNum),
      self.getChOpeningScene(chNum),
      self.getChFinalScenePrompt(chNum),
      self.getChFinalScene(chNum),
      self.getChContinuityPrompt(chNum),
      self.getChContinuity(chNum),
      '''For Chapter {chNum} of my book, write a detailed chapter outline taking into consideration my book's high-level outline, relevant characters and notable items, Chronology, Continuity Notes, and the Opening and Final scenes for Chapter {chNum}. The chapter outline must list all the scenes in the chapter and a short description of each. Begin the chapter outline with the Opening Scene from Chapter {chNum}, and finish the outline with the Final Scene from Chapter {chNum}.'''.format(chNum = chNum)
    ]
    self.setChOutline(
      chNum,
      self.chatAssistantResp(
        '''Ch {chNum} Outline'''.format(
          chNum = chNum
        ),
        chat
      )
    )
  
  def initLvl1Notes(
    self,
    initOutlinePrompt: str):
    self.info("""Setting prompt to write the high-level book outline to:
  
  """ + initOutlinePrompt)
    chat = [initOutlinePrompt]
    outline = self.chatAuthorResp(
      "Init Outline",
      chat
    )
    self.initOutline(outline)
    chat.append(outline)
    self.updateChCount()
    chat.append('''Taking into consideration my book's High-Level Outline, write a list of all the characters in my book. For each listed character include a short description of them and note where in the story they appear. Also list any notable items or objects in the story, with short descriptions.''')
    self.setCharDescsInit(
      self.chatAssistantResp(
        "Init Char Descrs",
        chat
      )
    )
    self.initProtagionist(
      self.chatAssistantResp(
        "Init Protagionist",
        [
          self.getOutlinePrompt(),
          self.getOutline(),
          self.getCharDescsPrompt(),
          self.getCharDescs(),
          '''What is the name of my book's protagionist, taking into consideration my book's High-Level Outline and Character Descriptions. Only return the name of my books protagionist.'''
        ]
      ).strip()
    )
    self.initTitle()
    
  def setBoundingScenes(
    self,
    chNum: int):
    chCount = self.getChCount()
    openingScenePrompt = """For Chapter {chNum} of my book, please write a detailed chapter outline describing the first, opening scene taking into consideration my book's high-level outline, characters and notable items, Chronology, and Continuity Notes. It should describe what happens in that opening scene and set up the story for the rest of the chapter. Do not summarize the entire chapter, only the first scene.""".format(chNum=chNum)
    if chNum > 1:
      openingScenePrompt += """The opening scene of Chapter {chNum} should directly follow the final scene of Chapter {prevChNum}""".format(
      chNum = chNum,
      prevChNum = chNum - 1)
    finalScenePrompt = """For Chapter {chNum} of my book, please write a detailed chapter outline describing the final scene of Chapter {chNum} taking into consideration my book's high-level outline, characters and notable items, Chronology, and Continuity Notes. It should describe what happens at the very end of the chapter, and set up the story for the opening scene of the next chapter, which will come immediately afterwards. Do not summarize the entire chapter, only the final scene.""".format(chNum=chNum)
    if chNum < chCount:
      finalScenePrompt += """The final scene of Chapter {chNum} should directly proceed the opening scene of Chapter {nextChNum}""".format(
      chNum = chNum,
      nextChNum = chNum + 1)
    chat = [
      self.getOutlinePrompt(),
      self.getOutline(),
      self.getProtagionistPrompt(),
      self.getProtagionist(),
      self.getContinuityPrompt(),
      self.getContinuity(),
      self.getCharDescsPrompt(),
      self.getCharDescs(),
      self.getChChronoPrompt(chNum),
      self.getChChrono(chNum),
      openingScenePrompt
    ]
    for i in range(4):
      action = '''Ch {chNum} Opening Scene'''.format(
        chNum = chNum
      )
      if i > 0:
        action = "Rewrite " + action
      openingScene=self.chatAssistantResp(
        action,
        chat + [openingScenePrompt]
      )
      if len(openingScene) > 100:
        self.setChOpeningScene(
          chNum,
          openingScene
        )
        break
    for i in range(4):
      action = '''Ch {chNum} Final Scene'''.format(chNum=chNum)
      if i > 0:
        action = "Rewrite " + action
      finalScene = self.chatAssistantResp(
        action,
        chat + 
        [
          self.getChOpeningScene(chNum),
          finalScenePrompt
        ]
      )
      if len(finalScene) > 100:
        self.setChFinalScene(
          chNum,
          finalScene)
      break
  
  def getChatIntResp(
    self,
    action: str,
    msgs: list[str]):
    for _ in range(6):
      respStr = re.sub(
        "[^0-9]",
        "", 
        self.chatAssistantResp(action, msgs)
      )
      if respStr != "":
        return int(respStr)
    self.warn("***Unable to parse int from chat response.")
    return -1
  
  def chatAssistantResp(
    self,
    action: str,
    msgs: list[str]):
    temp: float = self.assistant["temp"]
    sysRole: dict = {
      "role": "system",
      "content": self.assistant["descr"]}
    return self.getGptSmallModelResp(
      action,
      temp,
      sysRole,
      msgs)
  
  def chatAuthorResp(
    self,
    action: str,
    msgs: list[str]):
    temp: float = self.author["temp"]
    sysRole: dict = {
      "role": "system",
      "content": self.author["descr"]}
    if self.largeModelEnabled:
      return self.getGptLargeModelResp(
        action,
        temp,
        sysRole,
        msgs)
    return self.getGptSmallModelResp(
      action,
      temp,
      sysRole,
      msgs)
  
  def getGptSmallModelResp(
    self,
    action: str,
    temp: float,
    sysRole: dict,
    msgs: list[str]):
    try:
      return self.getSafeGptResp(
        action,
        chatModels["small"],
        temp,
        sysRole,
        msgs
      )
    except Exception as e:
      self.warn("***WARN: " + str(e))
      return ""
      
  def getGptLargeModelResp(
    self,
    action: str,
    temp: float,
    sysRole: dict,
    msgs: list[str]):
    try:
      return self.getSafeGptResp(
        action,
        chatModels["large"],
        temp,
        sysRole,
        msgs
      )
    except Exception as e:
      self.warn("***WARN: " + str(e))
      return ""
  
  def getSafeGptResp(
    self,
    action: str,
    model: str,
    temp: float,
    sysRole: dict,
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
      return self.getGptResp(
        action,
        model,
        temp,
        chatMsgs)
    except Exception as e:
      self.notice("Rsp Failed: " + str(e))
      time.sleep(15)
      try:
        return self.getGptResp(
          "Retry Failed " + action,
          model,
          temp,
          chatMsgs)
      except Exception as e:
        self.notice("Rsp Retry Failed: "+str(e))
        return "Failed Response Retry"
    
  def getGptResp(
    self,
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
    bookCost=self.getBookCost() + reqCost
    self.book["cost"] = str(bookCost)
    self.notice(
      "${:.5f}; ".format(bookCost)
      + model["id"] + "; "
      + action
      + " Req Sent")
    reqStart = time.time()
    reqHost = "api.openai.com"
    reqPath = "/v1/chat/completions"
    reqUrl = "https://"+reqHost+reqPath
    reqAuth = "Bearer " + self.apiKey
    reqHeaders = {
      "Content-Type": "application/json",
      "Authorization": reqAuth}
    reqParams = {
      "model": model["id"],
      "temperature": temp,
      "messages": msgs}
    postData = json.dumps(reqParams)
    response = self.simplePostRequest(
      url = reqUrl,
      headers = reqHeaders,
      data = postData,
      timeout = self.apiTimeout)
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
    tokensOut=usage["completion_tokens"]
    reqEnd = time.time()
    tokensInCost = tokensIn*inputCost
    tokensOutCost=tokensOut*outputCost
    totalCost=tokensInCost+tokensOutCost
    respCost = totalCost - reqCost
    bookCost=self.getBookCost()+respCost
    self.book["cost"] = str(bookCost)
    duration = int(reqEnd-reqStart)
    if duration < 2:
      duration = 2
    self.notice(
      "${:.5f}; ".format(bookCost)
      + model["id"] + "; "
      + "Rsp Received In " 
      + str(duration) + " secs")
    return respContent
  
  def simplePostRequest(
    self,
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
    
  def countTokens(
    self,
    messages: list[str]):
    tokens = 0
    for message in messages:
      tokens += len(message) / 4
    return tokens
    
  def rewriteIn1stPerson(
    self,
    content: str):
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
      protagionist = self.getProtagionist(),
      gradeLevel=self.getGradeLevelAsStr())
    altFirstPersonPrompt = '''Rewrite the following scene in first-person from {protagionist}'s point of view.
  
  Scene to rewrite:
  ```
  {contentToRewrite}
  ```'''.format(
      contentToRewrite = content,
      protagionist = self.getProtagionist())
    for i in range(6):
      resp = ""
      if i == 0:
        resp = self.chatAssistantResp(
          "Rewrite In First-Person",
          [firstPersonPrompt])
      elif i == 1:
        resp = self.chatAssistantResp(
          "Rewrite In First-Person",
          [altFirstPersonPrompt])
      elif i == 2:
        resp = self.chatAuthorResp(
          "Rewrite In First-Person",
          [firstPersonPrompt])
      else:
        resp = self.chatAuthorResp(
          "Rewrite In First-Person",
          [altFirstPersonPrompt])
      respContainsExclusion = False
      author = self.author
      if "respExclusion" in author:
        for val in author["respExclusion"]:
          if val in resp:
            respContainsExclusion = True
      if respContainsExclusion:
        continue
      if len(resp) > float(len(content)) * .8:
        return resp
    self.warn("***WARN: "
      + "Unable to convert content to "
      + "first-person perspective.")
    return content
  
  def debug(
    self,
    msg: str):
    divider = "------------------------------"
    self.logger.debug(divider)
    self.logger.debug(msg)
  
  def info(
    self,
    msg: str):
    divider = "------------------------------"
    self.logger.info(divider)
    self.logger.info(msg)
  
  def notice(
    self,
    msg: str):
    divider = "------------------------------"
    self.logger.warning(divider)
    self.logger.warning(msg)
  
  def warn(
    self,
    msg: str):
    divider = "------------------------------"
    self.logger.warning(divider)
    self.logger.warning(msg)
  
  def error(
    self,
    msg: str):
    divider = "------------------------------"
    self.logger.error(divider)
    self.logger.error(msg)
  
  def critical(
    self,
    msg: str):
    divider = "------------------------------"
    self.logger.warning(divider)
    self.logger.critical(msg)
  
  def getBookCost(self):
    if "cost" in self.book:
      return float(self.book["cost"])
    return 0.00
    
  def getPerspective(self):
    if self.firstPersonEnabled:
      return "first-person"
    else:
      return "third-person"
  
  def getGradeLevelAsInt(self):
    gradeLevel = self.gradeLevel
    if gradeLevel > 0 and gradeLevel < 21:
      return gradeLevel
    return 10
  
  def getGradeLevelAsStr(self):
    gradeLevel = self.getGradeLevelAsInt()
    if gradeLevel == 1:
      return "1st"
    if gradeLevel == 2:
      return "2nd"
    if gradeLevel == 3:
      return "3rd"
    if gradeLevel > 0 and gradeLevel < 21:
      return str(gradeLevel) + "th"
    return "10th"
    
  def getTargetChapterLength(self):
    gradeLevel = self.getGradeLevelAsInt()
    return gradeLevel * 300
    
  def getOutlinePrompt(self):
    return """Please print out my book's High-Level Outline. Include a list of characters and a short description of each character. Include a list of chapters and a short summary of what happens in each chapter."""
      
  def getOutline(self):
    return self.book["outline"]
  
  def initOutline(self, outline):
    if "highLevelOutline" not in self.book:
      self.info("Setting initial book outline to:\n\n" + outline)
      self.book["outline"] = outline
    
  def updateOutline(
    self,
    chNum: int):
    for i in range(4):
      chat = [
        self.getOutlinePrompt(),
        self.getOutline(),
        self.getProtagionistPrompt(),
        self.getProtagionist(),
        self.getContinuityPrompt(),
        self.getContinuity(),
        self.getCharDescsPrompt(),
        self.getCharDescs(),
        self.getChChronoPrompt(chNum),
        self.getChChrono(chNum),
        self.getChScenesPrompt(chNum),
        self.getChScenes(chNum),
        """Please edit and update my book's' high-level outline, taking into consideration my book's characters and notable items, Chronology, Continuity Notes, and draft of Chapter {chNum}. Print out the updated high-level outline for my book. Include a list of characters and a short description of each character. Include a list of chapters and a short summary of what happens in each chapter.""".format(chNum=chNum)
      ]
      action = "Update Book Outline"
      if i > 0:
        action = "Retry " + action
      outline = self.chatAssistantResp(
        action,
        chat)
      chat = [
        self.getOutlinePrompt(),
        outline,
        """Count and return as an integer the total number of chaters in my book's outline."""
      ]
      chCount = self.getChatIntResp(
        "Count Chapters",
        chat)
      if chCount >= self.getChCount():
        self.setOutline(outline)
        self.debug(
          p("Setting chapter count to:") +
          p(str(chCount))
        )
        self.book["chCount"] = str(chCount)
        break
  
  def setOutline(
    self,
    outline: str):
    self.debug("Setting book outline to:\n\n" + outline)
    self.book["outline"] = outline
    
  def getCharDescsPrompt(self):
    return """Please print out a list of my book's characters, with short descriptions of them, and all settings in the story, with short descriptions. Also list any notable items or objects in the story, with short descriptions."""
    
  def getCharDescs(self):
    return self.book["charDescs"]
    
  def setCharDescsInit(
    self,
    charDescs: str):
    self.info(p("Setting initial character descriptions to:") + p(charDescs))
    self.book["charDescs"] = charDescs
    
  def setCharDescs(
    self,
    charDescs: str):
    self.debug(p("Setting character descriptions to:") + p(charDescs))
    self.book["charDescs"] = charDescs
  
  def initProtagionist(
    self,
    charName: str):
    if "protagionist" not in self.book:
      self.debug("Setting protagionist to: " + charName)
      self.book["protagionist"] = charName
  
  def getProtagionist(self):
    return self.book["protagionist"]
  
  def getProtagionistPrompt(self):
    return '''Please print out my book's protagionist's name, who is also the main character of my book.'''
  
  def updateContinuity(
    self,
    chNum: int):
    chContPrompt = '''Please briefly note any important details or facts from Chapter {chNum} that you need to remember while writing the rest of my book, in order to ensure continuity and consistency.'''.format(
      chNum=chNum
    )
    self.setChContinuity(
      chNum,
      self.chatAssistantResp(
        "Update Chapter Continuity",
        [
          self.getOutlinePrompt(),
          self.getOutline(),
          self.getProtagionistPrompt(),
          self.getProtagionist(),
          self.getCharDescsPrompt(),
          self.getCharDescs(),
          self.getChChronoPrompt(chNum),
          self.getChChrono(chNum),
          self.getChDraftPrompt(chNum),
          self.getChDraft(chNum),
          chContPrompt
         ]
      )
    )
    continuity = ""
    if chNum > 5:
      condCont=""
      if "condCont" in self.book:
        condCont = self.book["condCont"],
      condContPrompt = '''Please summarize and rewrite more concisely my book's Continuity Notes that you will need to remember while writing the rest of the book, in order to ensure continuity and consistency.
  
  Continuity Notes:
  ```
  {condCont}
  {newCont}
  ```'''.format(
        condCont=condCont,
        newCont=self.getChContinuity(chNum-5))
      condCont = self.chatAssistantResp(
        "Condense Continuity",
        [condContPrompt]
      )
      self.debug("Setting Condensed Continuity Notes To:\n\n" + condCont)
      self.book["condCont"]=condCont
    chNumStart = 1
    chNumEnd = chNum + 1
    for i in range(chNumStart, chNumEnd):
      continuity += "\n" + self.getChContinuity(i)
    self.setContinuity(continuity)
    return continuity
  
  def updateCharDescs(
    self,
    chNum: int):
    chat = [
      self.getOutlinePrompt(),
      self.getOutline(),
      self.getProtagionistPrompt(),
      self.getProtagionist(),
      self.getContinuityPrompt(),
      self.getContinuity(),
      self.getCharDescsPrompt(),
      self.getCharDescs(),
      self.getChChronoPrompt(chNum),
      self.getChChrono(chNum),
      self.getChScenesPrompt(chNum),
      self.getChScenes(chNum),
      '''Please edit and update my book's lists of characters and notable items. Take into consideration my book's high-level outline, existing characters and notable items, Chronology, Continuity Notes, and draft of Chapter {chNum}. When listimg out characters please include a short descriptions of them. Also include a short description for each of the listed notable items.'''.format(chNum=chNum)
    ]
    charDescs=self.chatAssistantResp(
      "Update Char Descrs",
      chat)
    self.setCharDescs(charDescs)
    return charDescs
  
  def initTitle(self):
    chat = [
      self.getOutlinePrompt(),
      self.getOutline(),
      '''Please suggest a good title for my book taking into consideration my book's High-Level Outline. Make sure to respond with only the title.'''
    ]
    action = "Init Title"
    title = self.chatAuthorResp(
      action, chat)
    if "title:" in title.lower():
      title = title[title.find("title:") + 6].trim()
    self.info(p("Setting initial title to:"))
    self.critical(title)
    self.book["title"] = title
    
  def getContinuityPrompt(self):
    return '''Please briefly note any important details or facts from this book's from Continuity Notes that you need to remember while writing the rest of the book, in order to ensure continuity and consistency. Label these Continuity Notes.'''
  
  def getContinuity(self):
    return self.book["continuity"]
    
  def setContinuity(
    self,
    continuity: str):
    self.debug("Setting continuity notes to:\n\n" + continuity)
    self.book["continuity"] = continuity
  
  def updateChCount(self):
    chCount = self.getChatIntResp(
      "Count Chapters",
      [
        self.getOutlinePrompt(),
        self.getOutline(),
        '''Count and return as an integer the total number of chapters in my book's outline.'''
      ]
    )
    if chCount > 0:
      self.debug(
        p("Setting chapter count to:") +
        p(str(chCount))
      )
      self.book["chCount"] = str(chCount)
    
  def getChCount(self):
    return int(self.book["chCount"])
      
  def isLastCh(
    self,
    chNum: int):
    return chNum >= self.getChCount()
    
  def getChScenesPrompt(
    self,
    chNum: int):
    return """Please print out my book's draft of Chapter {chNum} that has all already happened and should not be repeated.""".format(chNum=chNum)
  
  def getChScenes(
    self,
    chNum: int):
    chapter = self.getChapter(chNum)
    scenes = chapter["scenes"]
    return p(p("* * *")).join(scenes)
  
  def getChapter(
    self,
    chNum: int):
    chKey = "ch" + str(chNum)
    return self.book["chapters"][chKey]
  
  def saveChapter(
    self,
    chNum: int,
    scenes: list[str]):
    if "chapters" not in self.book:
      self.book["chapters"] = {}
    chapters = self.book["chapters"]
    chapter = {}
    chapters["ch" + str(chNum)] = chapter
    chapter["scenes"] = scenes
    chapter["bookCost"] = self.book["cost"]
    chapter["bookTitle"] = self.book["title"]
    #updateOutline(chNum)
    outline = self.getOutline()
    chapter["bookOutline"] = outline
    bookChCount = self.getChCount()
    chapter["bookChCount"] = bookChCount
    bookIsDone = self.isLastCh(chNum)
    chapter["isBookDone"] = bookIsDone
    protag = self.getProtagionist()
    chapter["bookProtagionist"] = protag
    chapter["bookCharDescs"] = self.updateCharDescs(chNum)
    chapter["bookContinuity"] = self.updateContinuity(chNum)
    self.debug("""Saving Chapter {chNum} as:
  
  {chObj}""".format(
      chNum = chNum,
      chObj = chapter))
  
  def loadSaveState(
    self,
    chNum: int,
    save: dict):
    self.book.clear()
    for key in save:
      self.book[key] = save[key]
    prevCh = self.getChapter(chNum - 1)
    self.book["cost"] = prevCh["bookCost"]
    self.book["title"] = prevCh["bookTitle"]
    outline = prevCh["bookOutline"]
    self.book["outline"] = outline
    chCount = prevCh["bookChCount"]
    self.book["chCount"] = chCount
    protag = prevCh["bookProtagionist"]
    self.book["protagionist"] = protag
    charDescs = prevCh["bookCharDescs"]
    self.book["charDescs"] = charDescs
    continuity = prevCh["bookContinuity"]
    self.book["continuity"] = continuity
    isBookDone = prevCh["isBookDone"]
    self.book["theEnd"] = isBookDone
  
  def getChContinuityPrompt(
    self,
    chNum: int):
    return """Please briefly note any important details or facts from this book's Continuity Notes that you will need to remember while writing Chapter {chNum} of my book, in order to ensure continuity and consistency. Label these Continuity Notes.""".format(chNum=chNum)
    
  def setChContinuity(
    self,
    chNum: int,
    notes: str):
    self.debug(p("Setting chapter" + str(chNum) + " continuity notes to:") + p(notes))
    key = "ch" + str(chNum) + "Continuity"
    self.book[key] = notes
    
  def getChContinuity(
    self,
    chNum: int):
    key = "ch" + str(chNum) + "Continuity"
    return self.book[key]
       
  def getChCharDescPromptMsg(
    self,
    chNum: int):
    content=self.getChCharDescsPrompt(chNum)
    return {
      "role": "user",
      "content": content}
    
  def getChCharDescMsg(
    self,
    chNum: int):
    content=self.getChCharDescs(chNum)
    return {
      "role": "user",
      "content": content}
          
  def getChCharDescsPrompt(
    self,
    chNum: int):
    return """Please print out a list of my book's relevant characters, with short descriptions, that you will need to know about to write Chapter {chNum} of my book taking into consideration my book's high-level outline, characters and notable items, previou Chronological events, and Continuity Notes. Also list any notable items or objects in the story, with short descriptions, that you will need to know about to write Chapter {chNum} of my book.""".format(chNum=chNum)
    
  def setChCharDescs(
    self,
    chNum: int,
    descs: str):
    self.debug(p("Setting chapter" + str(chNum) + " character descriptions to:") + p(descs))
    key="ch" + str(chNum) + "CharDescs"
    self.book[key]=descs
    
  def getChCharDescs(
    self,
    chNum: int):
    key="ch" + str(chNum) + "CharDescs"
    return self.book[key]
  
  def updateChChrono(
    self,
    chNum: int):
    chronoPrompt = """Please print out the relevant chronological events that you will need to know about to write Chapter {chNum}of my book taking into consideration my book's high-level outline. The relevant chronological events for Chapter {chNum} should describe when the characters pass from one setting to another setting, when characters first meet each other, and anything else needed to ensure continuity and consistency during the writing process.""".format(chNum=chNum)
    chat = [
      self.getOutlinePrompt(),
      self.getOutline(),
      self.getProtagionistPrompt(),
      self.getProtagionist(),
      chronoPrompt
    ]
    self.setChChrono(
      chNum,
      self.chatAssistantResp(
        '''Update Ch {chNum} Chrono'''.format(chNum=chNum),
        chat
      )
    )
  
  def getChChronoPrompt(
    self,
    chNum: int):
    return """Please print out the relevant chronological events that you will need to know about to write Chapter {chNum} of my book.""".format(chNum=chNum)
  
  def setChChrono(
    self,
    chNum: int,
    chrono: str):
    self.debug(p("Setting chapter" + str(chNum) + " chrono to:") + p(chrono))
    key = "ch" + str(chNum) + "Chrono"
    self.book[key]=chrono
    
  def getChChrono(
    self,
    chNum: int):
    key="ch" + str(chNum) + "Chrono"
    return self.book[key]
  
  def getChOpeningScenePrompt(
    self,
    chNum: int):
    return "Please print out my book's opening scene for Chapter " + str(chNum)
    
  def setChOpeningScene(
    self,
    chNum: int,
    scene: str):
    self.debug(p("Setting chapter " + str(chNum) + " opening scene to:") + p(scene))
    key = "ch"+str(chNum)+"OpeningScene"
    self.book[key] = scene
    
  def getChOpeningScene(
    self,
    chNum: int):
    key = "ch"+str(chNum)+"OpeningScene"
    if key in self.book:
      return self.book[key]
    else:
      return """Please reference my book's High-Level Outline and Chronology to infer what the Opening Scene of Chapter {chNum} should be.""".format(chNum=chNum)
    
  def getChFinalScenePrompt(
    self,
    chNum: int):
    return "Please print out my book's final scene for Chapter " + str(chNum)
    
  def setChFinalScene(
    self,
    chNum: int,
    scene: str):
    self.debug(p("Setting chapter " + str(chNum) + " final scene to:") + p(scene))
    key = "ch" + str(chNum) + "FinalScene"
    self.book[key] = scene
    
  def getChFinalScene(
    self,
    chNum: int):
    key = "ch" + str(chNum) + "FinalScene"
    if key in self.book:
      return self.book[key]
    else:
      return """Please reference my book's High-Level Outline and Chronology to infer what the Final Scene of Chapter {chNum} should be.""".format(chNum=chNum)
  
  def getChOutlinePrompt(
    self,
    chNum: int):
    return "Please print out the chapter outline for my book's draft of Chapter " + str(chNum)
  
  def setChOutline(
    self,
    chNum: int,
    outline: str):
    self.debug("Setting outline of Chapter " + str(chNum) + " to:\n\n" + outline)
    key = "ch" + str(chNum) + "Outline"
    self.book[key] = outline
  
  def getChOutline(
    self,
    chNum: int):
    key = "ch" + str(chNum) + "Outline"
    return self.book[key]
  
  def getChDraftPrompt(
    self,
    chNum: int):
    return "Please print out my book's draft of Chapter " + str(chNum)
  
  def setChDraft(
    self,
    chNum: int,
    draft: str):
    self.debug("Setting draft of Chapter " + str(chNum) + " to:\n\n" + draft)
    key = "ch" + str(chNum) + "Draft"
    self.book[key] = draft
  
  def getChDraft(
    self,
    chNum: int):
    key = "ch" + str(chNum) + "Draft"
    return self.book[key]
  
  def getScenePrompt(
    self,
    chNum: int,
    sceneNum: int):
    return """For my book, please print out Scene {sceneNum} of Chapter {chNum}. The events of this scene have already happened, will not change, and must not be repeated.""".format(
      chNum = chNum,
      sceneNum = sceneNum)
  