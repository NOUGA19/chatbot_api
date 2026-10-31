# Chatbot procédures (FastAPI)

## Lancer
    pip install -r requirements.txt
    cp .env.example .env      # renseigner au moins une clé (Gemini ou Groq)
    uvicorn main:app --reload --port 8000

Clés : Gemini https://aistudio.google.com/apikey — Groq https://console.groq.com/keys

## Routes
- POST /chat  {"messages":[{"role":"user","content":"..."}], "mode":"text"|"assistant"} → texte en streaming
- GET /health → fournisseurs configurés
- GET /procedures → contenu des fiches (source de vérité partagée avec le site)

## Test
    curl -N -X POST localhost:8000/chat -H "Content-Type: application/json" \
      -d '{"messages":[{"role":"user","content":"Comment retirer mon relevé de notes ?"}],"mode":"assistant"}'

## Mettre à jour le contenu
Modifier procedures.md uniquement (relu à chaque requête, pas de redémarrage).
Si le modèle est refusé, changer GEMINI_MODEL / GROQ_MODEL dans .env.

## Architecture
Les 4 fiches (~2 000 tokens) tiennent dans le prompt : pas de RAG. Si le corpus grossit,
seule get_context() dans context.py est à remplacer.
# chatbot_api
