
class Template
{
public:
    template<typename T>
    Template( T &&t );

    template<typename ...T>
    Template( T &&...ts );

    template<typename R, typename T1, typename T2>
    R function( const T1 &t1, const T2 &t2 );

    template<typename ...T>
    void function( T &&...ts );
};
