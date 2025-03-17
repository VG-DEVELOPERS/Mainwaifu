// Ensure Telegram WebApp API is available
if (window.Telegram && Telegram.WebApp) {
    Telegram.WebApp.expand();  // Expand WebApp to full screen
    const userId = Telegram.WebApp.initDataUnsafe?.user?.id;

    if (userId) {
        fetchBalance(userId);
        fetchCharacters(userId);
    } else {
        console.error("Unable to fetch user ID.");
    }
} else {
    console.error("Telegram WebApp API not available.");
}

async function fetchBalance(userId) {
    try {
        let response = await fetch(`/shop/balance?user_id=${userId}`);
        let data = await response.json();
        document.getElementById("balance").innerText = `💰 Balance: ${data.balance} coins`;
    } catch (error) {
        console.error("Error fetching balance:", error);
    }
}

async function fetchCharacters(userId) {
    try {
        let response = await fetch("/shop/characters");
        let data = await response.json();
        let charactersDiv = document.getElementById("characters");
        charactersDiv.innerHTML = "";

        data.characters.forEach(character => {
            let charDiv = document.createElement("div");
            charDiv.classList.add("character");
            charDiv.innerHTML = `
                <h3>${character.name}</h3>
                <p>Rarity: ${character.rarity}</p>
                <p>Price: 💵${character.price}</p>
                <button onclick="buyCharacter('${character.id}', ${userId})">Buy</button>
            `;
            charactersDiv.appendChild(charDiv);
        });
    } catch (error) {
        console.error("Error fetching characters:", error);
    }
}

async function buyCharacter(characterId, userId) {
    try {
        let response = await fetch("/shop/purchase", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: userId, character_id: characterId })
        });

        let data = await response.json();
        alert(data.message);
        fetchBalance(userId);
    } catch (error) {
        console.error("Error purchasing character:", error);
    }
}
