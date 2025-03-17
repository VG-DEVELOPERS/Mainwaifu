document.addEventListener("DOMContentLoaded", () => {
    if (window.Telegram && Telegram.WebApp) {
        Telegram.WebApp.expand();
        const userId = Telegram.WebApp.initDataUnsafe?.user?.id;

        if (userId) {
            fetchBalance(userId);
            fetchCharacters(userId);
        } else {
            console.error("❌ Unable to get user ID.");
        }
    }
});

async function fetchBalance(userId) {
    let response = await fetch(`/shop/balance?user_id=${userId}`);
    let data = await response.json();
    document.getElementById("balance").innerText = `💰 Balance: ${data.balance} coins`;
}

async function fetchCharacters(userId) {
    let response = await fetch(`/shop/characters`);
    let data = await response.json();
    let charactersDiv = document.getElementById("characters");

    charactersDiv.innerHTML = "";
    data.characters.forEach(character => {
        let charCard = `
            <div class="character-card">
                <img src="${character.image_url}" alt="${character.name}">
                <h3>${character.name}</h3>
                <p>⭐ ${character.rarity} | 💰 ${character.price} coins</p>
                <button onclick="purchaseCharacter(${userId}, ${character.id})">Buy</button>
            </div>`;
        charactersDiv.innerHTML += charCard;
    });
}

async function purchaseCharacter(userId, characterId) {
    let response = await fetch(`/shop/purchase?user_id=${userId}&character_id=${characterId}`, { method: "POST" });
    let data = await response.json();
    
    alert(data.message || data.error);
    fetchBalance(userId);
}
