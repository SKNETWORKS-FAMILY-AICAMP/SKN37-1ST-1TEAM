"""Dinosaur Game Easter Egg Page."""
import streamlit as st
import streamlit.components.v1 as components

def render_dino_game():
    st.header("🦖 이스터에그: 공룡 게임")
    st.caption("사이드바 로고를 3번 클릭하여 해금되었습니다! 스페이스바 또는 화면을 클릭해 점프하세요.")

    dino_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body { text-align: center; font-family: sans-serif; background-color: #f7f7f7; margin: 0; padding: 10px; }
            #game { width: 600px; height: 200px; border-bottom: 2px solid #535353; margin: 20px auto; position: relative; overflow: hidden; background: #fff; border-radius: 8px; }
            #dino { width: 40px; height: 40px; position: absolute; bottom: 0; left: 50px; background: #535353; border-radius: 4px; }
            #cactus { width: 20px; height: 35px; position: absolute; bottom: 0; right: -20px; background: #e74c3c; border-radius: 3px; }
            @keyframes moveCactus {
                0% { right: -20px; }
                100% { right: 620px; }
            }
            .block { animation: moveCactus 1.4s infinite linear; }
            #score { font-size: 22px; font-weight: bold; color: #333; margin-top: 10px; }
            .jump-anim { animation: jump 0.5s ease-out; }
            @keyframes jump {
                0% { bottom: 0px; }
                50% { bottom: 100px; }
                100% { bottom: 0px; }
            }
        </style>
    </head>
    <body>
        <div id="score">Score: 0</div>
        <div id="game" onclick="jump()">
            <div id="dino"></div>
            <div id="cactus" class="block"></div>
        </div>
        <p>💡 <b>점프 방법:</b> 스페이스바 누르기 또는 게임 화면 클릭</p>

        <script>
            const dino = document.getElementById("dino");
            const cactus = document.getElementById("cactus");
            const scoreDisplay = document.getElementById("score");
            let score = 0;
            let isAlive = true;

            function jump() {
                if (!dino.classList.contains("jump-anim") && isAlive) {
                    dino.classList.add("jump-anim");
                    setTimeout(function () {
                        dino.classList.remove("jump-anim");
                    }, 500);
                }
            }

            document.addEventListener("keydown", function (event) {
                if (event.code === "Space") {
                    jump();
                }
            });

            let gameLoop = setInterval(function () {
                if (!isAlive) return;

                let dinoBottom = parseInt(window.getComputedStyle(dino).getPropertyValue("bottom"));
                let cactusLeft = parseInt(window.getComputedStyle(cactus).getPropertyValue("left"));

                if (cactusLeft < 90 && cactusLeft > 50 && dinoBottom <= 35) {
                    isAlive = false;
                    cactus.style.animation = "none";
                    alert("💥 Game Over! 최종 점수: " + Math.floor(score));
                    location.reload();
                } else {
                    score += 0.2;
                    scoreDisplay.innerText = "Score: " + Math.floor(score);
                }
            }, 10);
        </script>
    </body>
    </html>
    """
    components.html(dino_html, height=360)