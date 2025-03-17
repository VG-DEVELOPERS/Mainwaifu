if (window.Telegram && Telegram.WebApp) {
    Telegram.WebApp.expand();  // Expand WebApp full screen
    const userId = Telegram.WebApp.initDataUnsafe?.user?.id;

    if (userId) {
        fetchBalance(userId);
    } else {
        document.getElementById("balance").innerText = "Error: Unable to detect user ID.";
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
