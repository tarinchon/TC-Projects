// Declare and initialize global variables, deck, player_wins, and dealer_wins
let deck = [];
let player_wins = 0;
let dealer_wins = 0;
// Declare and initialize a global variable, player_sum, that keeps track of player's points
let player_sum = 0;
// Declare and initialize a global variable, dealer_sum, that keeps track of dealer's points
let dealer_sum = 0;

document.addEventListener("DOMContentLoaded", setUpDeck)

function reset_scoreboard() {
    document.getElementById("user_score").innerHTML = "0";
    document.getElementById("dealer_score").innerHTML = "0";
    player_wins = 0;
    dealer_wins = 0;
    sessionStorage.setItem("User", "0");
    sessionStorage.setItem("Dealer", "0"); 
}

function sleep(ms){
	return new Promise(resolve => setTimeout(resolve,ms));
}

function end_game(arg) {
    // Preserve scoreboard data across page refreshes
    sessionStorage.setItem("User", player_wins.toString());
    sessionStorage.setItem("Dealer", dealer_wins.toString());   
    // Annouce to user who won or that it's a tie  
    if (arg===0) {
        document.getElementById("user_score").innerHTML = player_wins;
        document.getElementById("start_new_game").innerHTML = "<p><h2>Congrats, you won the game!</h2></p>";
    } else if (arg===1) {
        document.getElementById("dealer_score").innerHTML = dealer_wins;
        document.getElementById("start_new_game").innerHTML = "<p><h2>Aw shucks, you lost</h2></p>";
    } else {
        document.getElementById("start_new_game").innerHTML = "<p><h2>It's a tie!</h2></p>";        
    }
    // Create a button for starting a new game
    let new_game_option = document.createElement("button");
    new_game_option.onclick = function() { 
        document.location.reload();
    };
    new_game_option.innerText = "Start New Game";
    document.getElementById("start_new_game").appendChild(new_game_option);
}

function add_to_player_sum(some_num) {
    if (["ace","jack","queen","king"].includes(some_num)) {
        if (some_num === "ace") {
            player_sum += 11;
        } else {
            player_sum += 10;
        }
    } else {
        player_sum += parseInt(some_num);
    }
}

function add_to_dealer_sum(some_num) {
    if (["ace","jack","queen","king"].includes(some_num)) {
        if (some_num === "ace") {
            dealer_sum += 11;
        } else {
            dealer_sum += 10;
        }
    } else {
        dealer_sum += parseInt(some_num);
    }
}

function playerHits() {
    // Pop card from top of shuffled deck
    let next_card = deck.pop();
    let some_num = next_card.split("_")[0]
    add_to_player_sum(some_num);
    // Append image to DOM, at the end of all of the user's cards
    let next_image = document.createElement("img");
    next_image.src = "images/" + next_card + ".png";
    document.querySelector("#user_cards").appendChild(next_image);
    // player busts
    if (player_sum > 21) {
        dealer_wins += 1;
        end_game(1);
    } else if (player_sum === 21) {
        playerStands();
    }
}

async function playerStands() {
    // the dealer's turn
    // Initialize array that will keep track of dealer's first 2 cards
    first_deal = []
    // Pop 2 cards for dealer's first hand
    first_deal.push(deck.pop());
    first_deal.push(deck.pop());
    /* The for loop below adds each card from the dealer's first hand 
    as an image to the HTML code and also adds the number of these cards
    to dealer_sum */
    for (let i=0; i < first_deal.length; i++) {
        let card = first_deal[i].split("_")[0]
        add_to_dealer_sum(card)
        let image = document.createElement("img");
        image.src = "images/" + first_deal[i] + ".png";
        await sleep(2000);
        document.querySelector("#dealer_cards").appendChild(image);
    }
    // Add cards to dealer's hand until dealer's total is at least 17
    while (dealer_sum < 17) {
        new_card = deck.pop();
        number = new_card.split("_")[0];
        add_to_dealer_sum(number);
        let card_image = document.createElement("img");
        card_image.src = "images/" + new_card + ".png";
        await sleep(2000);
        document.querySelector("#dealer_cards").appendChild(card_image);
    }
    // dealer busts
    if (dealer_sum > 21) {
        player_wins += 1;
        end_game(0);
    } else {
        // check for whoever has more points in their hand
        if (dealer_sum > player_sum) {
            dealer_wins += 1;
            end_game(1);
        } else if (player_sum > dealer_sum) {
            player_wins += 1;
            end_game(0);
        } else {
            end_game(2);
        }
    }
}

function startGame() {
    // Initialize array that will keep track of player's first 2 cards
    first_deal = [];
    // Pop 2 cards for first deal for player, before the player presses anything
    first_deal.push(deck.pop());
    first_deal.push(deck.pop());
    /* We will start with no cards/images for the player. The for loop below adds
    each card from the player's first deal as an image to the HTML code and also
    adds the number of these cards to player_sum */
    for (let i=0; i < first_deal.length; i++) {
        let card = first_deal[i].split("_")[0];
        add_to_player_sum(card);
        let image = document.createElement("img");
        image.src = "images/" + first_deal[i] + ".png";
        document.querySelector("#user_cards").appendChild(image);
    }
    // Player gets Blackjack and wins, ending game immediately
    if (player_sum === 21) {
        player_wins += 1;
        end_game(0);
    } else {
        /* If the player_sum is not 21 that means it's less than 21 and the user
        can choose to hit or stand */
        const event1 = document.querySelector("#user_hit");
        event1.addEventListener("click", playerHits);
        const event2 = document.querySelector("#user_stand");
        event2.addEventListener("click", playerStands);
    }
}

function shuffleDeck() {
    for (let i = 0; i < deck.length; i++) {
        let temp = deck[i];
        let randomNumber = Math.floor(Math.random() * deck.length);
        deck[i] = deck[randomNumber];
        deck[randomNumber] = temp;
    }
    startGame()
}

function setUpDeck() {
    // This function sets up the deck by creating an array that includes all 52 cards
    let player_score = sessionStorage.getItem("User");
    let dealerscore = sessionStorage.getItem("Dealer");
    if (player_score !== null && dealerscore !== null) {
        document.querySelector("#user_score").innerHTML = player_score;
        player_wins = parseInt(player_score);
        document.querySelector("#dealer_score").innerHTML = dealerscore;
        dealer_wins = parseInt(dealerscore);
    }
    const clubs = "_of_clubs"
    const diamonds = "_of_diamonds"
    const hearts = "_of_hearts"
    const spades = "_of_spades"
    const words = ["_of_clubs","_of_diamonds","_of_hearts", "_of_spades"]
    for (let i = 2; i < 11; i++) {
        deck.push(i.toString() + clubs);
        deck.push(i.toString() + diamonds);
        deck.push(i.toString() + hearts);
        deck.push(i.toString() + spades);
    }
    for (let i = 0; i < words.length; i++) {
        deck.push("ace" + words[i]);
        deck.push("jack" + words[i]);
        deck.push("queen" + words[i]);
        deck.push("king" + words[i]);
    }
    /* Call function, shuffleDeck, to shuffle the deck before starting the game
    and dealing out cards */
    shuffleDeck()
}

