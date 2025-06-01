function copyContent() {
    var e = document.getElementById("deps");
    e.select();
    e.setSelectionRange(0, 99999);
    navigator.clipboard.writeText(e.value);
}
