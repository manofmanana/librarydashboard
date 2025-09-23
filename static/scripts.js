document.addEventListener("DOMContentLoaded", function(){
  let imgs = document.querySelectorAll("img");
  imgs.forEach(img => {
    img.addEventListener("mouseover", () => img.style.transform = "scale(1.05)");
    img.addEventListener("mouseout", () => img.style.transform = "scale(1)");
    img.style.transition = "transform 0.2s ease";
  });
});
