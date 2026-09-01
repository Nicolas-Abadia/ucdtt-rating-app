# v1 Screenshots

Every page of the v1 server-rendered Django app, captured from the live deploy at <https://ucdtt-rating-app.onrender.com>.


## Public pages

Visible to anyone, no login required. (Features to modify data are shown only to officers)

### Leaderboard (dark)

![Leaderboard listing every player sorted by rating, highest first, in dark mode](leaderboard-screenshot.png "Leaderboard, dark color scheme")

### Leaderboard (light)

![The same leaderboard rendered in light mode](leaderboard-light-screenshot.png "Leaderboard, light color scheme")

### Player details

![Player detail page showing the player's current rating and their rating history](player-details-screenshot.png "Player details")

### Matches record

![List of every recorded match, most recent first](matches-record-screenshot.png "Matches record")

### Match details

![Match detail page showing the two players, the score, the date, and the rating change](match-details-screenshot.png "Match details")

## Officer pages

Behind login. Officers record matches, manage the roster, and manage their own account.

### Add new player

![Form for adding a player, with name and optional initial rating fields](add-player-screenshot.png "Add new player")

### Edit player

![Form for editing an existing player](edit-player-screenshot.png "Edit player")

### Add new match

![Form for recording a match: both players, both scores, and the date played](add-match-screenshot.png "Add new match")

### Edit match

![Form for editing an existing match](edit-match-screenshot.png "Edit match")

### Officer login

![Form to login as an existing officer](officer-login-screenshot.png "Officer login")

### Account

![Account page where a signed-in officer changes their own username or password](officer-account-screenshot.png "Officer account")

### New officer account

![Sign-up form used by an existing officer to create another officer account](new-officer-account-screenshot.png "New officer account")

## CSV imports

Both importers take one upload, show a preview of what would change, and write nothing until the preview is confirmed.

### Import players

![Player CSV import page listing the required columns and an example file](import-player-screenshot.png "Import players")

### Import players, preview and confirm

![Preview of an uploaded player CSV, reporting rows to be created and rows to be skipped, with Import and Discard buttons](import-player-confirmation-screenshot.png "Import players, preview and confirm")

### Import matches

![Match CSV import page listing the five required columns and the accepted date formats](import-match-screenshot.png "Import matches")

### Import matches, preview and confirm

![Preview of an uploaded match CSV, reporting rows to be created and rows to be skipped by line number, with Import and Discard buttons](import-match-confirmation-screenshot.png "Import matches, preview and confirm")


