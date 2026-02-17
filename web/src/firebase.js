import { initializeApp } from "firebase/app";
import { getDatabase, ref, set, onValue } from "firebase/database";

const firebaseConfig = {
    apiKey: "AIzaSyDVq6P1uTkmHpJi4yw3nq_jriRA1kLvlqE",
    authDomain: "hyva-rover.firebaseapp.com",
    databaseURL: "https://hyva-rover-default-rtdb.firebaseio.com",
    projectId: "hyva-rover",
    storageBucket: "hyva-rover.firebasestorage.app",
    messagingSenderId: "34964669413",
    appId: "1:34964669413:web:e31a1fa3a4d4be8c81a50c"
};

const app = initializeApp(firebaseConfig);
const database = getDatabase(app);

export { database, ref, set, onValue };
