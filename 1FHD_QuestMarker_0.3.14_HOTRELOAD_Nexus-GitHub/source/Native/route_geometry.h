typedef struct {float x,y;} RoutePoint;
static double rg_abs(double x) {return x<0?-x:x;}
static double rg_atan2(double y,double x) {
    double out;__asm__("fpatan":"=t"(out):"0"(x),"u"(y):"st(1)");return out;
}
static double rg_acos(double x) {
    if(x>1)x=1;
    if(x<-1)x=-1;
    return rg_atan2(rp_sqrt(1-x*x),x);
}
/* Shortest tangent/arc path outside the star's safe circle. */
static double rg_distance(RoutePoint a,RoutePoint b,double radius) {
    double dx=(double)a.x-b.x,dy=(double)a.y-b.y;
    double straight=rp_sqrt(dx*dx+dy*dy);
    if(radius<=0)return straight;
    double aa=(double)a.x*a.x+(double)a.y*a.y;
    double bb=(double)b.x*b.x+(double)b.y*b.y;
    if(aa<=radius*radius||bb<=radius*radius)return straight;
    double angle=rg_abs(rg_atan2((double)a.x*b.y-(double)a.y*b.x,(double)a.x*b.x+(double)a.y*b.y));
    double tangentAngles=rg_acos(radius/rp_sqrt(aa))+rg_acos(radius/rp_sqrt(bb));
    if(angle<=tangentAngles)return straight;
    return rp_sqrt(aa-radius*radius)+rp_sqrt(bb-radius*radius)+radius*(angle-tangentAngles);
}
static int rg_days(RoutePoint a,RoutePoint b,double radius,int speed) {
    double days=rg_distance(a,b,radius)/speed;
    int whole=(int)days;return whole+(days>whole+0.000001);
}
#define rg_hyper_days rp_hyper_days
