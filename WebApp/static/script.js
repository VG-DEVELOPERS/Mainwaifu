document.addEventListener("DOMContentLoaded", () => {
    if (window.Telegram && Telegram.WebApp) {
        Telegram.WebApp.expand();  // Expand Mini App for better visibility
        
        // Get user ID from Telegram WebApp API
        const userId = Telegram.WebApp.initDataUnsafe?.user?.id;

        if (userId) {
            console.log("✅ User ID detected:", userId);
            fetchBalance(userId);  // Auto-fetch balance using user ID
        } else {
            console.error("❌ Unable to get user ID.");
            document.getElementById("balance").innerText = "❌ Error: Unable to detect user ID.";
        }
    } else {
        console.error("❌ Telegram WebApp API not available.");
    }
});

async function fetchBalance(userId) {
    try {
        let response = await fetch(`/shop/balance?user_id=${userId}`);  // Send user ID automatically
        let data = await response.json();
        document.getElementById("balance").innerText = `💰 Balance: ${data.balance} coins`;
    } catch (error) {
        console.error("❌ Error fetching balance:", error);
    }
}
