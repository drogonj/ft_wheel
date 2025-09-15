// Système de patch notes avec localStorage
import { getCookie } from "./utils.js";

class PatchNotesManager {
    constructor() {
        this.storageKey = 'ft_wheel_seen_versions';
        this.init();
    }

    async init() {
        try {
            const response = await fetch('/api/patch-notes/');
            const data = await response.json();
            
            if (this.shouldShowPatchNotes(data.current_version)) {
                this.showPatchNotes(data.current_version, data.versions[data.current_version]);
            }
        } catch (error) {
            console.error('Erreur lors du chargement des patch notes:', error);
        }
    }

    shouldShowPatchNotes(currentVersion) {
        const seenVersions = this.getSeenVersions();
        return !seenVersions.includes(currentVersion);
    }

    getSeenVersions() {
        const stored = localStorage.getItem(this.storageKey);
        return stored ? JSON.parse(stored) : [];
    }

    markVersionAsSeen(version) {
        const seenVersions = this.getSeenVersions();
        if (!seenVersions.includes(version)) {
            seenVersions.push(version);
            localStorage.setItem(this.storageKey, JSON.stringify(seenVersions));
        }
    }

    showPatchNotes(version, versionData) {
        // Créer le popup avec le même style que les autres popups
        const popup = document.createElement('div');
        popup.className = 'patch-notes-popup';
        popup.innerHTML = `
            <div class="patch-notes-content">
                <div class="patch-notes-header">
                    <h2>${versionData.title}</h2>
                    <span class="patch-notes-version">v${version}</span>
                    <span class="patch-notes-close">&times;</span>
                </div>
                <div class="patch-notes-body">
                    <p class="patch-notes-date">📅 ${versionData.date}</p>
                    <div class="patch-notes-list">
                        <h3>✨ Nouveautés :</h3>
                        <ul>
                            ${versionData.notes.map(note => `<li>${note}</li>`).join('')}
                        </ul>
                    </div>
                </div>
                <div class="patch-notes-footer">
                    <button class="patch-notes-btn">Découvrir</button>
                </div>
            </div>
        `;

        document.body.appendChild(popup);

        // Afficher avec animation
        setTimeout(() => {
            popup.classList.add('show');
        }, 100);

        // Gérer la fermeture
        const closeBtn = popup.querySelector('.patch-notes-close');
        const continueBtn = popup.querySelector('.patch-notes-btn');

        const closePatchNotes = () => {
            popup.classList.remove('show');
            setTimeout(() => {
                popup.remove();
            }, 300);
            this.markVersionAsSeen(version);
        };

        closeBtn.addEventListener('click', closePatchNotes);
        continueBtn.addEventListener('click', closePatchNotes);
        
        // Fermer en cliquant à l'extérieur
        popup.addEventListener('click', (e) => {
            if (e.target === popup) {
                closePatchNotes();
            }
        });
    }
}

// Initialiser automatiquement
document.addEventListener('DOMContentLoaded', () => {
    new PatchNotesManager();
});
