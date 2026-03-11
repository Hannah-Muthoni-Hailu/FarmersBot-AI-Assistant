# FarmersBot
FarmersBot is an AI-powered assistant specifically designed for Kenyan farmers. It allows for crop growth simulation and analysis and has support for both text-based and audio based interaction.

## Quickstart
There are multiple options for testing out FarmerBot. Select the one most suitable for you.

### 1. Pre-deployed Server
A Render server has been deployed for this application and all requests are being sent to it. You can simply download the frontend code, build an APK and run the application on your phone. However, note that this method may result in slow loading time or some "Read Timed Out" errors since the server has been deployed on Render's free tier which spins down with inactivity.

To use this application with a pre-deployed server:
1. Install buildozer dependencies using ```sudo apt update
sudo apt install -y \
  build-essential git zip unzip openjdk-17-jdk \
  python3-pip python3-venv \
  autoconf libtool pkg-config zlib1g-dev \
  libncurses5-dev libncursesw5-dev \
  libtinfo5 cmake libffi-dev libssl-dev``` on Linux
2. Clone into the repository using ```git clone https://github.com/Hannah-Muthoni-Hailu/FarmersBot-AI-Assistant.git```
3. Cd into the frontend directory
4. Create a virtual environment in the frontend directory
5. Run ```pip install -r requirements.txt``` to install dependencies
6. Run ```pip install --upgrade pip setuptools wheel``` to upgrade pip and install wheels and setuptools
7. Run ```pip install kivy buildozer Cython==0.29.33``` to install buildozer and the Cython version that's compatible with this application
8. Run ```buildozer android debug``` (The buildozer.spec file has already been created for you with all the necessary requirements.) Note that this first build will take between 15-30 minutes depending on your system
9. Connect your phone to your computer using a USB and enable USB debugging (only Android phones are currently supported).
10. Run ```buildozer android deploy run``` to install the application. (You may get a warning stating that the application may be dangerous. This is because some older Kivy dependencies has been used which are not recognized by most modern Android phones. Whether you choose to trust this application is up to your own discretion.)
11. Create an account and start using the application.

You also have the option of using a pre-built APK stored in the frontend/bin folder. Simply follow steps 1, 2, 6, 7 and 10 above. This saves time so that you don't have to build the application from scratch but could lead to unexpected errors due to differences in computer sytems.

### 2. Local Application
You can choose to run the application locally on a computer using the following steps:
1. Clone into the repository using ```git clone https://github.com/Hannah-Muthoni-Hailu/FarmersBot-AI-Assistant.git```
2. Create a virtual environment
3. Run ```pip install -r requirements.txt``` seperately for both the frontend and backend since they use different requirements files.
4. From the root directory, run ```uvicorn backend.server:app --reload``` to start the server.
5. Change the URL requests in the frontend to point to your local server (They are currently pointing to a web service deployed on Render)
6. From the frontend directory, run ```python3 main.py``` to start the application frontend.

Note that this method is not preferred since a number of the frontend packages are specifically built for smartphones and may not be supported by most PC systems causing the application to crash. This is especially true for the audio and image recording features so you will be limited in the features you can use.
