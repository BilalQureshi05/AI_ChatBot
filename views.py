from django.shortcuts import render
from django.http import JsonResponse
import git
import os

def chat_view(request):
    return render(request, 'chat.html')

def get_response(request):
    user_message = request.GET.get('msg', '').lower().strip()
    
    if "hi" in user_message or "hello" in user_message:
        reply = "Hello"
    elif "who are you" in user_message:
        reply = "I am a Django bot, who is working on based rules."
    elif "how are you" in user_message:
        reply = "I am doing great, thanks for asking!"
    elif "time" in user_message:
        from datetime import datetime
        reply = f"{datetime.now().strftime('%H:%M')}"
    elif "connect me with github" in user_message:
        reply = "Sure! Here is the link to my GitHub profile: https://github.com/BilalQureshi05/Credit-Risk-Analysis"
    else:
        reply = "Sorry ! This option is not available."
        
    return JsonResponse({'reply': reply})


def clone_view(request):

    repo_url = request.POST.get('https://github.com/BilalQureshi05/Credit-Risk-Analysis').strip()

    folder_path = "C:/Users/bilal/OneDrive/Desktop/AI_ChatBot/AI_ChatBot/chat/cloned_repos/"

    if os.path.exists(folder_path):
        reply = "Repository already cloned."

    try:
        git.Repo.clone_from(repo_url, folder_path)
        reply = "Repository cloned successfully."
    except Exception as e:
        reply = f"Error cloning repository: {str(e)}"

    return JsonResponse({'reply': reply})