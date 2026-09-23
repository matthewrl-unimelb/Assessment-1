Included in your code repository should be:
## a README file that contains:

1. the URL to your deployed application.

https://assessment-1-h8ynbt4ebfhhhzg8zhpt4p.streamlit.app/

2. 1x test case that should be run to demonstrate the application’s functionality. 

# Tax law is notorious for having complicated ownership structures and money flows. This app allows the user to not only ask typical legal questions about the case (e.g. ratio, procedural history, and analysis) but also to draw relevant aspects of the case for an easier visual representation.

#In line with making tax cases easier to understand with the assistance of visualizations, I have also added a dropdown which allows the user to select the level of pre-existing knowledge that will alter the gpt-4o response accordingly. If the user would like to see a simpler or more complicated answer to their question, they can regenerate the answer and compare it with a different knowledge-level response.

Steps
0. Enter the wrong password
# The wrong password is rejected

1. Enter the provided password
# The correct password should grant access.

2. Enter your name and level of knowledge in tax from the drop down and click start
# You will be brought to the chat page which will have your selected knowledge as the default level of response.

3. Enter some questions into the chat (e.g. “What is a sham?”, “What is Cameron’s annual salary?”)
# A response according to your level will be generated.
# The response will cite to a page pinpoint (e.g. p.1068)
# If the answer to your question is not in the source document, the response will indicate that there is no answer to your question.

4. Click “Sources from the judgment”
# The excerpt(s) gpt-4o drew upon to generate its response will show in a collapsible box.

5. Click “Compare with another level” and select the comparison level from the dropdown
# Another response will be generated to the right of the existing response at the level selected. This may be done for each level.

6. Change the knowledge-level and ask a follow-up question (e.g. “Why did the court find that there was a sham?” [trick question])
# The chat has memory and will be able to build on the previous responses.
# The chat will use the selected knowledge level going forward unless another is selected.
# When given a trick question, the app will correct the premise.


6.a. Ask for a drawing or diagram (e.g. Please draw the ownership structure in this case)
# A drawing will appear visualizing the ownership structure followed by an explanation of the picture. 
#Note: you may re-generate the explanation at different levels but the same diagram will appear to ensure the level-comparison is one-to-one (rather than explaining slightly different diagrams).

7. Once you reach three (3) responses, as you should now, scroll to the top of the page and click “Show [X] earlier question(s)”
# It will show the third most recent response and all those earlier.
# The most recent response will be the only response fully visible. The second most recent response and its question will be visible but greyed out until the user hovers over it.

8. Save any of the previous messages to a new or existing folder
# The message (and any diagrams) will save to that folder which is accessible in the sidebar on the left of the screen
# You may collapse and adjust the size of the sidebar
# gpt-4o will name the folder for you along with a count of how many chats are saved in the folder

9. Save a new message to an existing folder
# gpt-4o will update the folder name and the chat count

10. Open the sidebar and select a folder by left clicking
# The chats in the folder will appear

11. Rename a folder manually
# If renamed, the folder will no longer automatically update the title when another response is saved to that folder. The message count will continue to increase.

12. Click “Back to chat” and ask another question. Save the response to the renamed folder
# The folder will close and you will be brought back to your previous chat session.
# The folder’s title will not update

13. Scroll to the bottom of one of the saved responses in the folder and click “Remove from folder.”
# The response count will decrease in the folder’s title and the response will be removed from the folder.

14. Return to the folder and click “Rename” of a manually renamed folder.
# If you wish to return to a gpt-4o generated title then click “Let AI name it.” 
# Adding more responses after clicking “Let AI name it” will revert to automatic updates to the title when new responses are added.

15. Click “Back to chat” and ask another question. Save the response to the renamed folder
# The folder will close and you will be brought back to your previous chat session.
# The folder’s title will update again.

16. Return to the folder and click “Download”
# You will also be able to download that folder as an .md file to your personal computer which includes the answers, the diagram code, and the sources.

17. In the folder, click “Delete”
# After clicking the confirmation, the folder will delete.
# You will be brought back to the chat.

18. Save a message from the chat into another folder
# A new folder is created and named by gpt-4o
# Important for steps 19-21.

19. Open the sidebar and left click “Clear chat”
# The chat will clear from the message history but saved responses will remain in the folders.

20. Close the application entirely from your browser and re-open the app. Repeat steps 1-2 BUT provide a different name
# No existing folders will be present.

21. Save a response to a new folder
# As before, a folder will be created.

22. Close the application entirely from your browser and re-open the app. Repeat steps 1-2 BUT provide the initial name
# Your saved folders will persist after app closure. Previously saved folders are only visible to those who enter the same name on app startup.  
# These ‘username’ saves will only persist while the app is running on Streamlit’s server. If the app stops running on Streamlit’s end, the folders will be gone (timeout ~ 15-2- minutes).

3. any artefacts required for the tests. For example, if your application includes file upload functionality, please provide any relevant files that are intended to be uploaded.

No artefacts are required for the app to run – all files are 

In lieu of the user providing their API credential – I have password protected the app with a password that literally nobody would be able to guess.
